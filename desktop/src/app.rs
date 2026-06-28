use iced::executor;
use iced::widget::{button, column, container, horizontal_rule, row, scrollable, text, text_input};
use iced::{clipboard, Application, Command, Element, Length, Settings, Theme};
use serde::{Deserialize, Serialize};

const BACKEND_URL: &str = "http://127.0.0.1:8420";

#[derive(Debug, Clone)]
pub enum Message {
    TracesLoaded(Vec<TraceSummary>),
    TraceSelected(String),
    TraceLoaded(TraceDetail),
    StepSelected(usize),
    Noop,
    ForkRequested(usize),
    ForkNameChanged(String),
    ForkModelChanged(String),
    ForkConfirmed,
    ForkCancelled,
    BranchCreated(String),
    BranchesLoaded(Vec<BranchSummary>),
    BranchSelected(String),
    BranchLoaded(BranchDetail),
    ToggleCostPanel,
    GenerateTest,
    TestGenerated(String),
    CopyTestToClipboard,
    ExportTrace,
    TraceExported(String),
    CopyExportToClipboard,
    ShowImportPanel,
    ImportJsonChanged(String),
    ImportTrace,
    TraceImported,
    CloseExportPanel,
    CloseImportPanel,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TraceSummary {
    pub id: String,
    pub agent_name: String,
    pub step_count: u32,
    pub total_cost: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TraceDetail {
    pub id: String,
    pub agent_name: String,
    pub steps: Vec<StepDetail>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct StepDetail {
    pub index: usize,
    pub step_type: String,
    pub name: String,
    pub tokens_in: u32,
    pub tokens_out: u32,
    pub cost: f64,
    pub duration_ms: u64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct BranchSummary {
    pub id: String,
    pub name: String,
    pub fork_step_index: usize,
    pub step_count: u32,
    pub total_cost: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct BranchDetail {
    pub id: String,
    pub name: String,
    pub parent_trace_id: String,
    pub fork_step_index: usize,
    pub modifications: Vec<Modification>,
    pub steps: Vec<StepDetail>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Modification {
    pub field: String,
    pub old_value: String,
    pub new_value: String,
}

#[derive(Serialize)]
struct ForkRequest {
    branch_name: String,
    model_name: String,
}

pub struct App {
    traces: Vec<TraceSummary>,
    selected_trace: Option<TraceDetail>,
    selected_step: Option<usize>,
    branches: Vec<BranchSummary>,
    selected_branch: Option<BranchDetail>,
    fork_step_index: Option<usize>,
    fork_name: String,
    fork_model: String,
    show_cost_panel: bool,
    generated_test: Option<String>,
    test_loading: bool,
    export_json: Option<String>,
    show_export_panel: bool,
    show_import_panel: bool,
    import_json: String,
    import_loading: bool,
}

impl Application for App {
    type Executor = executor::Default;
    type Flags = ();
    type Message = Message;
    type Theme = Theme;

    fn new(_flags: ()) -> (Self, Command<Self::Message>) {
        (
            App {
                traces: Vec::new(),
                selected_trace: None,
                selected_step: None,
                branches: Vec::new(),
                selected_branch: None,
                fork_step_index: None,
                fork_name: String::new(),
                fork_model: String::new(),
                show_cost_panel: false,
                generated_test: None,
                test_loading: false,
                export_json: None,
                show_export_panel: false,
                show_import_panel: false,
                import_json: String::new(),
                import_loading: false,
            },
            fetch_traces(),
        )
    }

    fn title(&self) -> String {
        String::from("Agent Flight Recorder")
    }

    fn update(&mut self, message: Self::Message) -> Command<Self::Message> {
        match message {
            Message::TracesLoaded(traces) => {
                self.traces = traces;
            }
            Message::TraceSelected(id) => {
                self.selected_branch = None;
                self.branches.clear();
                self.generated_test = None;
                self.test_loading = false;
                return fetch_trace_detail(id);
            }
            Message::TraceLoaded(detail) => {
                let trace_id = detail.id.clone();
                self.selected_trace = Some(detail);
                self.selected_step = None;
                self.selected_branch = None;
                self.generated_test = None;
                self.test_loading = false;
                return fetch_branches(trace_id);
            }
            Message::StepSelected(index) => {
                self.selected_step = Some(index);
            }
            Message::Noop => {}
            Message::ForkRequested(step_index) => {
                self.fork_step_index = Some(step_index);
                self.fork_name = String::new();
                self.fork_model = String::new();
            }
            Message::ForkNameChanged(name) => {
                self.fork_name = name;
            }
            Message::ForkModelChanged(model) => {
                self.fork_model = model;
            }
            Message::ForkConfirmed => {
                if let (Some(trace), Some(_)) =
                    (&self.selected_trace, self.fork_step_index)
                {
                    let trace_id = trace.id.clone();
                    let branch_name = self.fork_name.clone();
                    let model_name = self.fork_model.clone();
                    self.fork_step_index = None;
                    self.fork_name.clear();
                    self.fork_model.clear();
                    return fork_trace(trace_id, branch_name, model_name);
                }
            }
            Message::ForkCancelled => {
                self.fork_step_index = None;
                self.fork_name.clear();
                self.fork_model.clear();
            }
            Message::BranchCreated(branch_id) => {
                self.fork_step_index = None;
                if let Some(trace) = &self.selected_trace {
                    let trace_id = trace.id.clone();
                    return Command::batch(vec![
                        fetch_branches(trace_id),
                        fetch_branch_detail(branch_id),
                    ]);
                }
            }
            Message::BranchesLoaded(branches) => {
                self.branches = branches;
            }
            Message::BranchSelected(branch_id) => {
                return fetch_branch_detail(branch_id);
            }
            Message::BranchLoaded(detail) => {
                self.selected_branch = Some(detail);
                self.selected_step = None;
            }
            Message::ToggleCostPanel => {
                self.show_cost_panel = !self.show_cost_panel;
            }
            Message::GenerateTest => {
                if let Some(trace) = &self.selected_trace {
                    self.test_loading = true;
                    self.generated_test = None;
                    let trace_id = trace.id.clone();
                    return generate_test(trace_id);
                }
            }
            Message::TestGenerated(code) => {
                self.test_loading = false;
                self.generated_test = Some(code);
            }
            Message::CopyTestToClipboard => {
                if let Some(code) = &self.generated_test {
                    return clipboard::write(code.clone());
                }
            }
            Message::ExportTrace => {
                if let Some(trace) = &self.selected_trace {
                    let trace_id = trace.id.clone();
                    return export_trace(trace_id);
                }
            }
            Message::TraceExported(json) => {
                self.export_json = Some(json);
                self.show_export_panel = true;
                self.show_import_panel = false;
            }
            Message::CopyExportToClipboard => {
                if let Some(json) = &self.export_json {
                    return clipboard::write(json.clone());
                }
            }
            Message::ShowImportPanel => {
                self.show_import_panel = true;
                self.show_export_panel = false;
                self.import_json.clear();
            }
            Message::ImportJsonChanged(json) => {
                self.import_json = json;
            }
            Message::ImportTrace => {
                if !self.import_json.trim().is_empty() {
                    self.import_loading = true;
                    let json = self.import_json.clone();
                    return import_trace(json);
                }
            }
            Message::TraceImported => {
                self.import_loading = false;
                self.show_import_panel = false;
                self.import_json.clear();
                return fetch_traces();
            }
            Message::CloseExportPanel => {
                self.show_export_panel = false;
                self.export_json = None;
            }
            Message::CloseImportPanel => {
                self.show_import_panel = false;
                self.import_json.clear();
            }
        }
        Command::none()
    }

    fn view(&self) -> Element<'_, Self::Message> {
        let sidebar = self.view_sidebar();
        let cost_btn_label = if self.show_cost_panel { "Timeline" } else { "Cost" };
        let header = container(
            row![
                text("Agent Flight Recorder").size(18),
                button(text(cost_btn_label).size(13))
                    .on_press(Message::ToggleCostPanel)
                    .padding(4),
            ]
            .spacing(12)
            .align_items(iced::Alignment::Center),
        )
        .padding(8)
        .width(Length::Fill);

        let middle: Element<'_, Message> = if self.show_export_panel {
            self.view_export_panel()
        } else if self.show_import_panel {
            self.view_import_panel()
        } else if self.show_cost_panel {
            self.view_cost_analysis()
        } else {
            self.view_timeline()
        };

        let inspector = self.view_inspector();

        let main_area = column![header, horizontal_rule(1), middle, horizontal_rule(1), inspector]
            .spacing(0)
            .width(Length::Fill)
            .height(Length::Fill);

        row![sidebar, main_area]
            .spacing(0)
            .width(Length::Fill)
            .height(Length::Fill)
            .into()
    }

    fn theme(&self) -> Self::Theme {
        Theme::Dark
    }
}

fn fetch_traces() -> Command<Message> {
    let url = format!("{}/api/traces", BACKEND_URL);
    Command::perform(
        async move {
            match reqwest::get(&url).await {
                Ok(resp) => match resp.json::<Vec<TraceSummary>>().await {
                    Ok(traces) => Message::TracesLoaded(traces),
                    Err(_) => Message::Noop,
                },
                Err(_) => Message::Noop,
            }
        },
        |msg| msg,
    )
}

fn fetch_trace_detail(id: String) -> Command<Message> {
    let url = format!("{}/api/traces/{}", BACKEND_URL, id);
    Command::perform(
        async move {
            match reqwest::get(&url).await {
                Ok(resp) => match resp.json::<TraceDetail>().await {
                    Ok(detail) => Message::TraceLoaded(detail),
                    Err(_) => Message::Noop,
                },
                Err(_) => Message::Noop,
            }
        },
        |msg| msg,
    )
}

fn fetch_branches(trace_id: String) -> Command<Message> {
    let url = format!("{}/api/traces/{}/branches", BACKEND_URL, trace_id);
    Command::perform(
        async move {
            match reqwest::get(&url).await {
                Ok(resp) => match resp.json::<Vec<BranchSummary>>().await {
                    Ok(branches) => Message::BranchesLoaded(branches),
                    Err(_) => Message::Noop,
                },
                Err(_) => Message::Noop,
            }
        },
        |msg| msg,
    )
}

fn fetch_branch_detail(branch_id: String) -> Command<Message> {
    let url = format!("{}/api/branches/{}", BACKEND_URL, branch_id);
    Command::perform(
        async move {
            match reqwest::get(&url).await {
                Ok(resp) => match resp.json::<BranchDetail>().await {
                    Ok(detail) => Message::BranchLoaded(detail),
                    Err(_) => Message::Noop,
                },
                Err(_) => Message::Noop,
            }
        },
        |msg| msg,
    )
}

fn generate_test(trace_id: String) -> Command<Message> {
    let url = format!("{}/api/traces/{}/generate-test", BACKEND_URL, trace_id);
    Command::perform(
        async move {
            let client = reqwest::Client::new();
            match client.post(&url).send().await {
                Ok(resp) => {
                    if resp.status().is_success() {
                        match resp.text().await {
                            Ok(code) => Message::TestGenerated(code),
                            Err(_) => Message::Noop,
                        }
                    } else {
                        Message::Noop
                    }
                }
                Err(_) => Message::Noop,
            }
        },
        |msg| msg,
    )
}

fn export_trace(trace_id: String) -> Command<Message> {
    let url = format!("{}/api/traces/{}/export", BACKEND_URL, trace_id);
    Command::perform(
        async move {
            match reqwest::get(&url).await {
                Ok(resp) => {
                    if resp.status().is_success() {
                        match resp.text().await {
                            Ok(json) => Message::TraceExported(json),
                            Err(_) => Message::Noop,
                        }
                    } else {
                        Message::Noop
                    }
                }
                Err(_) => Message::Noop,
            }
        },
        |msg| msg,
    )
}

fn import_trace(json: String) -> Command<Message> {
    let url = format!("{}/api/traces/import", BACKEND_URL);
    Command::perform(
        async move {
            let client = reqwest::Client::new();
            match client
                .post(&url)
                .header("Content-Type", "application/json")
                .body(json)
                .send()
                .await
            {
                Ok(resp) => {
                    if resp.status().is_success() {
                        Message::TraceImported
                    } else {
                        Message::Noop
                    }
                }
                Err(_) => Message::Noop,
            }
        },
        |msg| msg,
    )
}

fn fork_trace(trace_id: String, branch_name: String, model_name: String) -> Command<Message> {
    let url = format!("{}/api/traces/{}/fork", BACKEND_URL, trace_id);
    Command::perform(
        async move {
            let client = reqwest::Client::new();
            let body = ForkRequest {
                branch_name,
                model_name,
            };
            match client.post(&url).json(&body).send().await {
                Ok(resp) => {
                    if resp.status().is_success() {
                        match resp.json::<BranchDetail>().await {
                            Ok(detail) => Message::BranchCreated(detail.id),
                            Err(_) => Message::Noop,
                        }
                    } else {
                        Message::Noop
                    }
                }
                Err(_) => Message::Noop,
            }
        },
        |msg| msg,
    )
}

impl App {
    fn view_sidebar(&self) -> Element<'_, Message> {
        let trace_items: Vec<Element<'_, Message>> = self
            .traces
            .iter()
            .map(|t| {
                let id = t.id.clone();
                button(
                    column![
                        text(&t.agent_name).size(14),
                        text(format!("{} steps · ${:.4}", t.step_count, t.total_cost)).size(12),
                    ]
                    .spacing(4)
                    .padding(8),
                )
                .on_press(Message::TraceSelected(id))
                .width(Length::Fill)
                .into()
            })
            .collect();

        let mut sidebar_col = column![
            row![
                text("Traces").size(20),
                button(text("Import").size(12))
                    .on_press(Message::ShowImportPanel)
                    .padding(4),
            ]
            .spacing(8)
            .align_items(iced::Alignment::Center),
            horizontal_rule(1),
            scrollable(column(trace_items).spacing(2))
        ]
        .spacing(8)
        .padding(12);

        if self.selected_trace.is_some() {
            sidebar_col = sidebar_col.push(
                button(text("Export Trace").size(13))
                    .on_press(Message::ExportTrace)
                    .padding(6)
                    .width(Length::Fill),
            );
        }

        if !self.branches.is_empty() {
            let branch_items: Vec<Element<'_, Message>> = self
                .branches
                .iter()
                .map(|b| {
                    let id = b.id.clone();
                    let is_selected = self
                        .selected_branch
                        .as_ref()
                        .map_or(false, |sb| sb.id == b.id);
                    let label = if is_selected { ">> " } else { "" };
                    button(
                        column![
                            text(format!("{}{}", label, b.name)).size(14),
                            text(format!(
                                "{} steps · ${:.4} · fork@{}",
                                b.step_count, b.total_cost, b.fork_step_index
                            ))
                            .size(12),
                        ]
                        .spacing(4)
                        .padding(8),
                    )
                    .on_press(Message::BranchSelected(id))
                    .width(Length::Fill)
                    .into()
                })
                .collect();

            sidebar_col = sidebar_col
                .push(horizontal_rule(1))
                .push(text("Branches").size(18))
                .push(scrollable(column(branch_items).spacing(2)));
        }

        container(sidebar_col)
            .width(250)
            .height(Length::Fill)
            .into()
    }

    fn view_timeline(&self) -> Element<'_, Message> {
        let content: Element<'_, Message> = match &self.selected_trace {
            Some(trace) => {
                let step_items: Vec<Element<'_, Message>> = trace
                    .steps
                    .iter()
                    .map(|s| {
                        let idx = s.index;
                        let mut row_items: Vec<Element<'_, Message>> = vec![
                            text(format!("[{}]", s.step_type)).size(13).into(),
                            text(&s.name).size(13).into(),
                            text(format!("${:.4}", s.cost)).size(13).into(),
                        ];

                        if self.fork_step_index == Some(idx) {
                            row_items.push(text("(forking)").size(12).into());
                        } else {
                            row_items.push(
                                button(text("Fork").size(12))
                                    .on_press(Message::ForkRequested(idx))
                                    .padding(2)
                                    .into(),
                            );
                        }

                        button(row(row_items).spacing(12).padding(6))
                            .on_press(Message::StepSelected(idx))
                            .width(Length::Fill)
                            .into()
                    })
                    .collect();

                let mut timeline_col = column![scrollable(column(step_items).spacing(2))];

                if self.fork_step_index.is_some() {
                    let fork_dialog = container(
                        column![
                            text("Create Branch (Fork)").size(16),
                            text_input("Branch name", &self.fork_name)
                                .on_input(Message::ForkNameChanged),
                            text_input("Model name", &self.fork_model)
                                .on_input(Message::ForkModelChanged),
                            row![
                                button("Confirm").on_press(Message::ForkConfirmed),
                                button("Cancel").on_press(Message::ForkCancelled),
                            ]
                            .spacing(8),
                        ]
                        .spacing(8)
                        .padding(12),
                    )
                    .width(Length::Fill);

                    timeline_col = timeline_col.push(horizontal_rule(1)).push(fork_dialog);
                }

                timeline_col.spacing(8).into()
            }
            None => text("Select a trace to view timeline").size(14).into(),
        };

        container(
            column![text("Timeline").size(20), horizontal_rule(1), content]
                .spacing(8)
                .padding(12),
        )
        .height(Length::FillPortion(2))
        .into()
    }

    fn view_cost_analysis(&self) -> Element<'_, Message> {
        let steps = match &self.selected_trace {
            Some(trace) => &trace.steps,
            None => {
                return container(
                    column![
                        text("Cost Analysis").size(20),
                        horizontal_rule(1),
                        text("Select a trace to view cost analysis").size(14),
                    ]
                    .spacing(8)
                    .padding(12),
                )
                .height(Length::FillPortion(2))
                .into();
            }
        };

        if steps.is_empty() {
            return container(
                column![
                    text("Cost Analysis").size(20),
                    horizontal_rule(1),
                    text("No steps in this trace").size(14),
                ]
                .spacing(8)
                .padding(12),
            )
            .height(Length::FillPortion(2))
            .into();
        }

        let total_cost: f64 = steps.iter().map(|s| s.cost).sum();

        let max_idx = steps
            .iter()
            .enumerate()
            .max_by(|a, b| a.1.cost.partial_cmp(&b.1.cost).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, _)| i)
            .unwrap_or(0);

        let mut sorted: Vec<(usize, &StepDetail)> = steps.iter().enumerate().collect();
        sorted.sort_by(|a, b| b.1.cost.partial_cmp(&a.1.cost).unwrap_or(std::cmp::Ordering::Equal));

        let mut items: Vec<Element<'_, Message>> = Vec::new();
        items.push(text(format!("Total Cost: ${:.4}", total_cost)).size(18).into());
        items.push(horizontal_rule(1).into());
        items.push(text("Steps by cost (descending):").size(14).into());

        let mut cumulative = 0.0f64;
        for (orig_idx, step) in &sorted {
            cumulative += step.cost;
            let pct = if total_cost > 0.0 { step.cost / total_cost * 100.0 } else { 0.0 };
            let is_max = *orig_idx == max_idx;

            let label = text(format!(
                "#{} [{}] {}  ${:.4} ({:.1}%)  cum: ${:.4}  {}ms",
                step.index, step.step_type, step.name, step.cost, pct, cumulative, step.duration_ms
            ))
            .size(13);

            let row: Element<'_, Message> = if is_max {
                // Highlight the most expensive step using a container with distinct styling
                container(
                    text(format!(
                        "#{} [{}] {}  ${:.4} ({:.1}%)  cum: ${:.4}  {}ms  << MOST EXPENSIVE",
                        step.index, step.step_type, step.name, step.cost, pct, cumulative, step.duration_ms
                    ))
                    .size(13),
                )
                .padding(4)
                .into()
            } else {
                label.into()
            };

            items.push(row);
        }

        container(
            column![text("Cost Analysis").size(20), horizontal_rule(1), scrollable(column(items).spacing(4))]
                .spacing(8)
                .padding(12),
        )
        .height(Length::FillPortion(2))
        .into()
    }

    fn view_inspector(&self) -> Element<'_, Message> {
        let content: Element<'_, Message> = match (&self.selected_trace, &self.selected_branch, self.selected_step) {
            (_, Some(branch), Some(idx)) => match branch.steps.get(idx) {
                Some(step) => {
                    let mut items: Vec<Element<'_, Message>> = vec![
                        text(format!("[BRANCH: {}]", branch.name)).size(16).into(),
                        text(format!("Step #{}", step.index)).size(14).into(),
                        text(format!("Type: {}", step.step_type)).into(),
                        text(format!("Name: {}", step.name)).into(),
                        text(format!("Tokens In: {}", step.tokens_in)).into(),
                        text(format!("Tokens Out: {}", step.tokens_out)).into(),
                        text(format!("Cost: ${:.4}", step.cost)).into(),
                        text(format!("Duration: {}ms", step.duration_ms)).into(),
                    ];

                    if !branch.modifications.is_empty() {
                        items.push(horizontal_rule(1).into());
                        items.push(text("Modifications:").size(14).into());
                        for m in &branch.modifications {
                            items.push(
                                text(format!("{}: {} -> {}", m.field, m.old_value, m.new_value))
                                    .size(12)
                                    .into(),
                            );
                        }
                    }

                    if let Some(parent_trace) = &self.selected_trace {
                        items.push(horizontal_rule(1).into());
                        items.push(text("Comparison vs parent trace:").size(14).into());
                        let parent_cost: f64 = parent_trace.steps.iter().map(|s| s.cost).sum();
                        let branch_cost: f64 = branch.steps.iter().map(|s| s.cost).sum();
                        let parent_dur: u64 = parent_trace.steps.iter().map(|s| s.duration_ms).sum();
                        let branch_dur: u64 = branch.steps.iter().map(|s| s.duration_ms).sum();
                        items.push(
                            text(format!(
                                "Steps: {} (branch) vs {} (parent)",
                                branch.steps.len(),
                                parent_trace.steps.len()
                            ))
                            .into(),
                        );
                        items.push(
                            text(format!(
                                "Cost: ${:.4} (branch) vs ${:.4} (parent) [{}]",
                                branch_cost,
                                parent_cost,
                                format_delta(branch_cost - parent_cost)
                            ))
                            .into(),
                        );
                        items.push(
                            text(format!(
                                "Duration: {}ms (branch) vs {}ms (parent) [{}]",
                                branch_dur,
                                parent_dur,
                                format_delta_i64(branch_dur as i64 - parent_dur as i64)
                            ))
                            .into(),
                        );
                    }

                    column(items).spacing(4).into()
                }
                None => text("Step not found").into(),
            },
            (Some(trace), _, Some(idx)) => match trace.steps.get(idx) {
                Some(step) => column![
                    text(format!("Step #{}", step.index)).size(16),
                    text(format!("Type: {}", step.step_type)),
                    text(format!("Name: {}", step.name)),
                    text(format!("Tokens In: {}", step.tokens_in)),
                    text(format!("Tokens Out: {}", step.tokens_out)),
                    text(format!("Cost: ${:.4}", step.cost)),
                    text(format!("Duration: {}ms", step.duration_ms)),
                ]
                .spacing(4)
                .into(),
                None => text("Step not found").into(),
            },
            _ => text("Select a step to inspect").size(14).into(),
        };

        let mut inspector_col = column![
            text("Inspector").size(20),
            horizontal_rule(1),
            content,
        ]
        .spacing(8)
        .padding(12);

        if self.selected_trace.is_some() {
            inspector_col = inspector_col.push(horizontal_rule(1));

            let gen_btn_label = if self.test_loading {
                "Generating..."
            } else {
                "Generate Test"
            };
            let mut gen_btn = button(text(gen_btn_label).size(13)).padding(6);
            if !self.test_loading {
                gen_btn = gen_btn.on_press(Message::GenerateTest);
            }
            inspector_col = inspector_col.push(gen_btn);

            if let Some(code) = &self.generated_test {
                let test_content: Element<'_, Message> = column![
                    row![
                        text("Generated Test").size(16),
                        button(text("Copy").size(12))
                            .on_press(Message::CopyTestToClipboard)
                            .padding(4),
                    ]
                    .spacing(8)
                    .align_items(iced::Alignment::Center),
                    horizontal_rule(1),
                    scrollable(
                        container(
                            text(code.as_str()).size(12)
                        )
                        .padding(8)
                    )
                    .height(Length::Fill),
                ]
                .spacing(4)
                .into();

                inspector_col = inspector_col.push(test_content);
            }
        }

        container(inspector_col)
            .height(Length::FillPortion(1))
            .into()
    }

    fn view_export_panel(&self) -> Element<'_, Message> {
        let content: Element<'_, Message> = match &self.export_json {
            Some(json) => column![
                row![
                    text("Export Trace").size(20),
                    button(text("Copy").size(12))
                        .on_press(Message::CopyExportToClipboard)
                        .padding(4),
                    button(text("Close").size(12))
                        .on_press(Message::CloseExportPanel)
                        .padding(4),
                ]
                .spacing(8)
                .align_items(iced::Alignment::Center),
                horizontal_rule(1),
                scrollable(
                    container(text(json.as_str()).size(12))
                        .padding(8)
                )
                .height(Length::Fill),
            ]
            .spacing(8)
            .into(),
            None => column![
                text("Export Trace").size(20),
                horizontal_rule(1),
                text("Loading...").size(14),
            ]
            .spacing(8)
            .into(),
        };

        container(content)
            .padding(12)
            .width(Length::Fill)
            .height(Length::Fill)
            .into()
    }

    fn view_import_panel(&self) -> Element<'_, Message> {
        let import_btn_label = if self.import_loading {
            "Importing..."
        } else {
            "Import"
        };
        let mut import_btn = button(text(import_btn_label).size(13)).padding(6);
        if !self.import_loading && !self.import_json.trim().is_empty() {
            import_btn = import_btn.on_press(Message::ImportTrace);
        }

        column![
            row![
                text("Import Trace").size(20),
                import_btn,
                button(text("Close").size(12))
                    .on_press(Message::CloseImportPanel)
                    .padding(4),
            ]
            .spacing(8)
            .align_items(iced::Alignment::Center),
            horizontal_rule(1),
            text("Paste exported trace JSON below:").size(14),
            text_input("Paste JSON here...", &self.import_json)
                .on_input(Message::ImportJsonChanged)
                .padding(8),
        ]
        .spacing(8)
        .padding(12)
        .width(Length::Fill)
        .height(Length::Fill)
        .into()
    }
}

fn format_delta(val: f64) -> String {
    if val > 0.0 {
        format!("+${:.4}", val)
    } else if val < 0.0 {
        format!("-${:.4}", -val)
    } else {
        "no change".to_string()
    }
}

fn format_delta_i64(val: i64) -> String {
    if val > 0 {
        format!("+{}ms", val)
    } else if val < 0 {
        format!("-{}ms", -val)
    } else {
        "no change".to_string()
    }
}

pub fn run() -> iced::Result {
    App::run(Settings {
        window: iced::window::Settings {
            size: iced::Size::new(1200.0, 800.0),
            ..iced::window::Settings::default()
        },
        ..Settings::default()
    })
}
