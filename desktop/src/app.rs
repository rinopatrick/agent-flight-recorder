use iced::executor;
use iced::widget::{button, column, container, horizontal_rule, row, scrollable, text};
use iced::{Application, Command, Element, Length, Settings, Theme};
use serde::Deserialize;

const BACKEND_URL: &str = "http://127.0.0.1:8420";

#[derive(Debug, Clone)]
pub enum Message {
    TracesLoaded(Vec<TraceSummary>),
    TraceSelected(String),
    TraceLoaded(TraceDetail),
    StepSelected(usize),
    Noop,
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

pub struct App {
    traces: Vec<TraceSummary>,
    selected_trace: Option<TraceDetail>,
    selected_step: Option<usize>,
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
                return fetch_trace_detail(id);
            }
            Message::TraceLoaded(detail) => {
                self.selected_trace = Some(detail);
                self.selected_step = None;
            }
            Message::StepSelected(index) => {
                self.selected_step = Some(index);
            }
            Message::Noop => {}
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

        container(
            column![
                text("Traces").size(20),
                horizontal_rule(1),
                scrollable(column(trace_items).spacing(2))
            ]
            .spacing(8)
            .padding(12),
        )
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
                        button(
                            row![
                                text(format!("[{}]", s.step_type)).size(13),
                                text(&s.name).size(13),
                                text(format!("${:.4}", s.cost)).size(13),
                            ]
                            .spacing(12)
                            .padding(6),
                        )
                        .on_press(Message::StepSelected(idx))
                        .width(Length::Fill)
                        .into()
                    })
                    .collect();
                scrollable(column(step_items).spacing(2)).into()
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
        let content: Element<'_, Message> = match (&self.selected_trace, self.selected_step) {
            (Some(trace), Some(idx)) => match trace.steps.get(idx) {
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

pub fn run() -> iced::Result {
    App::run(Settings {
        window: iced::window::Settings {
            size: iced::Size::new(1200.0, 800.0),
            ..iced::window::Settings::default()
        },
        ..Settings::default()
    })
}
