use sysmonitor::types::{AppConfig, MonitoringState};

#[test]
fn test_monitoring_state_creation() {
    let config = AppConfig::default();
    let state = MonitoringState::new(config);

    assert_eq!(state.metrics_history.len(), 0);
    assert_eq!(state.active_alerts.len(), 0);
    assert!(!state.is_running);
}

#[test]
fn test_monitoring_state_add_metrics() {
    let config = AppConfig::default();
    let mut state = MonitoringState::new(config);

    // Create a mock metrics entry
    let metrics = sysmonitor::types::SystemMetrics {
        timestamp: chrono::Utc::now(),
        cpu: sysmonitor::types::CpuMetrics {
            usage_percent: 50.0,
            core_usage: vec![50.0, 50.0],
            load_average: (1.0, 1.0, 1.0),
            frequency_mhz: Some(3000),
        },
        memory: sysmonitor::types::MemoryMetrics {
            total_bytes: 16000000000000,
            used_bytes: 8000000000000,
            available_bytes: 8000000000000,
            swap_total_bytes: 2000000000000,
            swap_used_bytes: 0,
            usage_percent: 50.0,
        },
        disk: vec![],
        network: vec![],
    };

    state.add_metrics(metrics);

    assert_eq!(state.metrics_history.len(), 1);
    assert!(state.get_latest_metrics().is_some());
}

#[test]
fn test_monitoring_state_history_size() {
    let mut config = AppConfig::default();
    config.history_size = 5;

    let mut state = MonitoringState::new(config);

    // Add more metrics than history_size
    for i in 0..10 {
        let metrics = sysmonitor::types::SystemMetrics {
            timestamp: chrono::Utc::now(),
            cpu: sysmonitor::types::CpuMetrics {
                usage_percent: i as f32,
                core_usage: vec![i as f32],
                load_average: (1.0, 1.0, 1.0),
                frequency_mhz: Some(3000),
            },
            memory: sysmonitor::types::MemoryMetrics::default(),
            disk: vec![],
            network: vec![],
        };
        state.add_metrics(metrics);
    }

    // History should be bounded
    assert_eq!(state.metrics_history.len(), 5);
}
