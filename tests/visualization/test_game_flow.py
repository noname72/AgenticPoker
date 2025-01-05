import pytest
from visualization.game_flow import GameFlowVisualizer, InteractiveGameFlow, Node, PhaseType


def test_game_flow_visualization():
    """Test that the game flow visualization can be created without errors."""
    visualizer = GameFlowVisualizer()
    
    # Test adding a single node
    test_node = Node('test', 'Test Node', PhaseType.BETTING)
    visualizer.add_node(test_node)
    
    # Test adding an edge
    visualizer.add_edge('test', 'test', 'Test Edge')
    
    # Test creating complete flow
    visualizer.create_game_flow()
    
    # Test rendering (this will create a file)
    try:
        visualizer.render('test_flow')
    except Exception as e:
        pytest.fail(f"Failed to render graph: {str(e)}") 

def test_interactive_mode():
    """Test interactive visualization features."""
    flow = InteractiveGameFlow()
    flow.create_game_flow()
    
    # Test phase highlighting
    flow.highlight_active_phase('pre_draw_betting')
    flow.render('interactive_test')
    
    # Verify highlight was applied
    assert flow.active_phase == 'pre_draw_betting'

def test_metrics_collection():
    """Test game flow metrics collection."""
    flow = GameFlowVisualizer()
    flow.create_game_flow()
    
    # Record some test metrics
    flow.metrics.record_phase_duration('pre_draw_betting', 15.5)
    flow.metrics.record_transition('pre_draw_betting', 'discard')
    
    # Verify metrics were recorded
    assert len(flow.metrics.phase_durations['pre_draw_betting']) == 1
    assert flow.metrics.transition_counts[('pre_draw_betting', 'discard')] == 1 