use iced::executor;
use iced::widget::{button, column, container, horizontal_rule, row, scrollable, text, text_input};
use iced::{Application, Command, Element, Length, Settings, Theme};
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
                return fetch_trace_detail(id);
            }
            Message::TraceLoaded(detail) => {
                let trace_id = detail.id.clone();
                self.selected_trace = Some(detail);
                self.selected_step = None;
                self.selected_branch = None;
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
        }
        Command::none()
    }

    fn view(&self) -> Element<'_, Self::Message> {
        let sidebar = self.view_sidebar();
        let timeline = self.view_timeline();
        let inspector = self.view_inspector();

        let main_area = column![timeline, horizontal_rule(1), inspector]
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
            text("Traces").size(20),
            horizontal_rule(1),
            scrollable(column(trace_items).spacing(2))
        ]
        .spacing(8)
        .padding(12);

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

        container(
            column![text("Inspector").size(20), horizontal_rule(1), content]
                .spacing(8)
                .padding(12),
        )
        .height(Length::FillPortion(1))
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
