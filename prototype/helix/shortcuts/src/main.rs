use serde::Deserialize;
use std::collections::BTreeMap;
use unicode_width::UnicodeWidthChar;
#[cfg(test)]
use unicode_width::UnicodeWidthStr;
use zellij_tile::prelude::*;

#[derive(Deserialize)]
struct Catalogue {
    entries: Vec<Entry>,
}
#[derive(Clone, Deserialize)]
struct Entry {
    category: String,
    keys: String,
    context: String,
    description: String,
}
#[derive(Clone, Debug)]
struct Line {
    text: String,
    style: u8,
}
#[derive(Debug)]
struct Layout {
    lines: Vec<Line>,
    columns: usize,
    column_width: usize,
    height: usize,
}
impl Layout {
    fn max_scroll(&self, viewport: usize) -> usize {
        self.height.saturating_sub(viewport)
    }
    fn line(&self, column: usize, row: usize) -> Option<&Line> {
        if column >= self.columns || row >= self.height {
            None
        } else {
            self.lines.get(column * self.height + row)
        }
    }
}

fn clip(text: &str, width: usize) -> String {
    let mut result = String::new();
    let mut used = 0;
    for c in text.chars() {
        let size = c.width().unwrap_or(0);
        if used + size > width {
            break;
        }
        result.push(c);
        used += size;
    }
    result
}
fn wrap(text: &str, width: usize) -> Vec<String> {
    if width == 0 {
        return vec![];
    }
    let mut lines = vec![];
    let mut line = String::new();
    let mut used = 0;
    for c in text.chars() {
        let size = c.width().unwrap_or(0);
        if used + size > width && !line.is_empty() {
            lines.push(std::mem::take(&mut line));
            used = 0;
        }
        if size <= width {
            line.push(c);
            used += size;
        }
    }
    if !line.is_empty() {
        lines.push(line);
    }
    lines
}
fn layout(entries: &[Entry], query: &str, width: usize) -> (Layout, usize) {
    let query = query.to_lowercase();
    let entries: Vec<_> = entries
        .iter()
        .filter(|entry| {
            query.is_empty()
                || format!(
                    "{} {} {} {}",
                    entry.category, entry.keys, entry.context, entry.description
                )
                .to_lowercase()
                .contains(&query)
        })
        .collect();
    let matches = entries.len();
    let columns = ((width + 3) / 55).clamp(1, 3).min(matches.max(1));
    let column_width = width.saturating_sub((columns - 1) * 3) / columns;
    let mut blocks = vec![];
    let mut category = String::new();
    for entry in entries {
        let mut block = vec![];
        if category != entry.category {
            if !blocks.is_empty() {
                block.push(Line {
                    text: String::new(),
                    style: 0,
                });
            }
            category.clone_from(&entry.category);
            block.extend(
                wrap(&category, column_width)
                    .into_iter()
                    .map(|text| Line { text, style: 1 }),
            );
        }
        block.extend(
            wrap(&entry.keys, column_width)
                .into_iter()
                .map(|text| Line { text, style: 2 }),
        );
        let detail = format!("{} · {}", entry.context, entry.description);
        block.extend(
            wrap(&detail, column_width.saturating_sub(1))
                .into_iter()
                .map(|text| Line {
                    text: format!(" {text}"),
                    style: 0,
                }),
        );
        blocks.push(block);
    }
    if matches == 0 {
        blocks.push(vec![Line {
            text: clip("没有匹配的快捷键；Ctrl+U 清除搜索", column_width),
            style: 0,
        }]);
    }
    let target = blocks.iter().map(Vec::len).sum::<usize>().div_ceil(columns);
    let mut packed = vec![vec![]; columns];
    let mut column = 0;
    for block in blocks {
        if column + 1 < columns
            && !packed[column].is_empty()
            && packed[column].len() + block.len() > target
        {
            column += 1;
        }
        packed[column].extend(block);
    }
    let height = packed.iter().map(Vec::len).max().unwrap_or(0);
    let mut lines = vec![];
    for mut column in packed {
        column.resize(
            height,
            Line {
                text: String::new(),
                style: 0,
            },
        );
        lines.extend(column);
    }
    (
        Layout {
            lines,
            columns,
            column_width,
            height,
        },
        matches,
    )
}

#[derive(Default)]
struct State {
    entries: Vec<Entry>,
    query: String,
    searching: bool,
    scroll: usize,
    rows: usize,
    cols: usize,
    first_pipe: bool,
}
register_plugin!(State);
impl State {
    fn viewport(&self) -> usize {
        self.rows.saturating_sub(3).max(1)
    }
    fn scroll_by(&mut self, amount: isize) {
        let (layout, _) = layout(&self.entries, &self.query, self.cols);
        self.scroll = self
            .scroll
            .saturating_add_signed(amount)
            .min(layout.max_scroll(self.viewport()));
    }
    fn key(&mut self, key: KeyWithModifier) -> bool {
        if key.has_no_modifiers() && matches!(key.bare_key, BareKey::Esc | BareKey::F(4)) {
            close_self();
            return false;
        }
        if key.bare_key == BareKey::Char('u') && key.has_modifiers(&[KeyModifier::Ctrl]) {
            self.query.clear();
            self.scroll = 0;
            return true;
        }
        if self.searching && key.has_modifiers(&[KeyModifier::Shift]) {
            if let BareKey::Char(mut character) = key.bare_key {
                character.make_ascii_uppercase();
                self.query.push(character);
                self.scroll = 0;
                return true;
            }
        }
        if !key.has_no_modifiers() {
            return false;
        }
        match key.bare_key {
            BareKey::Up => self.scroll_by(-1),
            BareKey::Down => self.scroll_by(1),
            BareKey::PageUp => self.scroll_by(-(self.viewport() as isize)),
            BareKey::PageDown => self.scroll_by(self.viewport() as isize),
            BareKey::Home => self.scroll = 0,
            BareKey::End => self.scroll = usize::MAX,
            BareKey::Char('/') if !self.searching => {
                self.searching = true;
                self.scroll = 0;
            }
            BareKey::Enter => self.searching = false,
            BareKey::Backspace if self.searching => {
                self.query.pop();
                self.scroll = 0;
            }
            BareKey::Char(c) if self.searching && !c.is_control() => {
                self.query.push(c);
                self.scroll = 0;
            }
            _ => return false,
        }
        true
    }
}
impl ZellijPlugin for State {
    fn load(&mut self, _configuration: BTreeMap<String, String>) {
        self.entries = serde_json::from_str::<Catalogue>(include_str!("../shortcuts.json"))
            .expect("validated shortcut catalogue")
            .entries;
        self.first_pipe = true;
        subscribe(&[EventType::Key, EventType::Mouse]);
    }
    fn pipe(&mut self, message: PipeMessage) -> bool {
        if message.name != "toggle-shortcuts" {
            return false;
        }
        if self.first_pipe {
            self.first_pipe = false;
            show_self(true);
            true
        } else {
            close_self();
            false
        }
    }
    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::Key(key) => self.key(key),
            Event::Mouse(Mouse::ScrollUp(lines)) => {
                self.scroll_by(-(lines as isize));
                true
            }
            Event::Mouse(Mouse::ScrollDown(lines)) => {
                self.scroll_by(lines as isize);
                true
            }
            _ => false,
        }
    }
    fn render(&mut self, rows: usize, cols: usize) {
        self.rows = rows;
        self.cols = cols;
        if rows == 0 || cols == 0 {
            return;
        }
        let (layout, matches) = layout(&self.entries, &self.query, cols);
        let viewport = rows.saturating_sub(3);
        self.scroll = self.scroll.min(layout.max_scroll(viewport));
        print!("\x1b[0m\x1b[2J\x1b[H\x1b[?25l");
        let header = if self.searching {
            format!("搜索：{}▏  Enter 结束输入；Esc 关闭窗口", self.query)
        } else if self.query.is_empty() {
            format!("默认快捷键 · {matches} 项 · Ctrl / Shift / Alt 使用完整名称")
        } else {
            format!("搜索：{} · {matches} 项 · Ctrl+U 清除", self.query)
        };
        print!("\x1b[1;1H\x1b[1;37m{}\x1b[0m", clip(&header, cols));
        if rows > 1 {
            print!(
                "\x1b[2;1H\x1b[90m{}\x1b[0m",
                clip(
                    "按使用场景区分；“→”表示依次按键。语言与调试操作需要对应服务。",
                    cols
                )
            );
        }
        for column in 0..layout.columns {
            for row in 0..viewport {
                if let Some(line) = layout.line(column, self.scroll + row) {
                    let style = match line.style {
                        1 => "1;33",
                        2 => "1;36",
                        _ => "37",
                    };
                    print!(
                        "\x1b[{};{}H\x1b[{}m{}\x1b[0m",
                        row + 3,
                        column * (layout.column_width + 3) + 1,
                        style,
                        line.text
                    );
                }
            }
        }
        if rows > 2 {
            let position = format!("{}/{}", self.scroll + 1, layout.max_scroll(viewport) + 1);
            let footer = format!(
                "F4 / Esc 关闭  |  / 搜索  |  滚轮 / PageUp / PageDown 翻页  |  {position}"
            );
            print!("\x1b[{};1H\x1b[90m{}\x1b[0m", rows, clip(&footer, cols));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn entries() -> Vec<Entry> {
        serde_json::from_str::<Catalogue>(include_str!("../shortcuts.json"))
            .unwrap()
            .entries
    }
    #[test]
    fn catalogue_is_complete_and_has_full_modifier_names() {
        let entries = entries();
        assert!(entries.len() > 100);
        for command in ["Ctrl+Shift+S", "Ctrl+Shift+F", "F12", "Space → c → i", "F4"] {
            assert!(
                entries.iter().any(|entry| entry.keys == command),
                "{command}"
            );
        }
    }
    #[test]
    fn columns_reflow_and_every_line_stays_inside_the_window() {
        for width in [1, 8, 24, 54, 55, 80, 108, 110, 160, 180, 240] {
            let (layout, _) = layout(&entries(), "", width);
            for line in &layout.lines {
                assert!(
                    line.text.width() <= layout.column_width,
                    "{width}: {}",
                    line.text
                );
            }
            assert!(layout.columns * layout.column_width + (layout.columns - 1) * 3 <= width);
        }
        let short = layout(&entries(), "ctrl+shift+s", 180).0;
        assert!(short.line(0, short.height).is_none());
        assert_eq!(short.columns, 1);
        assert_eq!(layout(&entries(), "", 80).0.columns, 1);
        assert_eq!(layout(&entries(), "", 120).0.columns, 2);
        assert_eq!(layout(&entries(), "", 180).0.columns, 3);
    }
    #[test]
    fn filtering_matches_keys_description_context_and_unicode() {
        for query in ["ctrl+shift+s", "编译器", "文件树", "断点"] {
            assert!(layout(&entries(), query, 80).1 > 0);
        }
        assert_eq!(layout(&entries(), "no-such-shortcut", 80).1, 0);
    }
    #[test]
    fn scrolling_and_tiny_viewports_are_bounded() {
        let mut state = State {
            entries: entries(),
            rows: 5,
            cols: 25,
            ..Default::default()
        };
        state.scroll_by(isize::MAX);
        let max = layout(&state.entries, "", 25)
            .0
            .max_scroll(state.viewport());
        assert_eq!(state.scroll, max);
        state.scroll_by(isize::MIN);
        assert_eq!(state.scroll, 0);
        for width in [0, 1, 2] {
            let (layout, _) = layout(&state.entries, "", width);
            assert!(layout
                .lines
                .iter()
                .all(|line| line.text.width() <= layout.column_width));
        }
    }
    #[test]
    fn wide_unicode_is_not_split_into_half_cells() {
        assert_eq!(clip("宏A", 1), "");
        assert_eq!(clip("宏A", 2), "宏");
        assert_eq!(wrap("宏ABC", 3), vec!["宏A", "BC"]);
    }
}
