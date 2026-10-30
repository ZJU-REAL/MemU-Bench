"""Utility functions for memory generation."""


def format_action_qwen3_5(event: dict, width: int, height: int) -> str:
    """Format an action event for Qwen3.5 (coordinates normalized by *999)."""
    action_type = event.get('type', 'unknown')

    if action_type == 'tap':
        x, y = int(event['x'] * 999), int(event['y'] * 999)
        return f"User clicked at position [{x}, {y}]"
    elif action_type == 'long_press':
        x, y = int(event['x'] * 999), int(event['y'] * 999)
        duration = event.get('duration', 0)
        return f"User long-pressed at position [{x}, {y}] for {duration:.2f} seconds"
    elif action_type == 'swipe':
        x1, y1 = int(event['start_x'] * 999), int(event['start_y'] * 999)
        x2, y2 = int(event['end_x'] * 999), int(event['end_y'] * 999)
        return f"User swiped from [{x1}, {y1}] to [{x2}, {y2}]"
    elif action_type == 'key_press':
        key = event.get('key_name', 'unknown')
        button = "Back" if key == "back" else "Home" if key == "home" else "Recents" if key == "recents" else key
        return f"User pressed the {button} button"
    else:
        return f"Unknown action: {action_type}"


def format_action_qwen3vl(event: dict, width: int, height: int) -> str:
    """Format an action event for Qwen3VL (coordinates normalized by *999)."""
    action_type = event.get('type', 'unknown')

    if action_type == 'tap':
        x, y = int(event['x'] * 999), int(event['y'] * 999)
        return f"User clicked at position [{x}, {y}]"
    elif action_type == 'long_press':
        x, y = int(event['x'] * 999), int(event['y'] * 999)
        duration = event.get('duration', 0)
        return f"User long-pressed at position [{x}, {y}] for {duration:.2f} seconds"
    elif action_type == 'swipe':
        x1, y1 = int(event['start_x'] * 999), int(event['start_y'] * 999)
        x2, y2 = int(event['end_x'] * 999), int(event['end_y'] * 999)
        return f"User swiped from [{x1}, {y1}] to [{x2}, {y2}]"
    elif action_type == 'key_press':
        key = event.get('key_name', 'unknown')
        button = "Back" if key == "back" else "Home" if key == "home" else "Recents" if key == "recents" else key
        return f"User pressed the {button} button"
    else:
        return f"Unknown action: {action_type}"


def format_action_agentic(event: dict, width: int, height: int) -> str:
    """Format an action event for Agentic (raw float coordinates, no normalization)."""
    action_type = event.get('type', 'unknown')

    if action_type == 'tap':
        return f"User clicked at position [{event.get('x', 0):.4f}, {event.get('y', 0):.4f}]"
    elif action_type == 'long_press':
        return f"User long-pressed at position [{event.get('x', 0):.4f}, {event.get('y', 0):.4f}] for {event.get('duration', 0):.2f} seconds"
    elif action_type == 'swipe':
        return (f"User swiped from [{event.get('start_x', 0):.4f}, {event.get('start_y', 0):.4f}] "
                f"to [{event.get('end_x', 0):.4f}, {event.get('end_y', 0):.4f}]")
    elif action_type == 'key_press':
        key = event.get('key_name', 'unknown')
        button = "Back" if key == "back" else "Home" if key == "home" else "Recents" if key == "recents" else key
        return f"User pressed the {button} button"
    else:
        return f"Unknown action: {action_type}"


def format_action_mai_ui(event: dict, width: int, height: int) -> str:
    """Format an action event for Mai-UI (coordinates normalized by *999, swipe uses direction).

    Mai-UI uses direction-based swipe (finger movement direction) instead of
    coordinate-based swipe, and lowercase button names.
    """
    action_type = event.get('type', 'unknown')

    if action_type == 'tap':
        x, y = int(event['x'] * 999), int(event['y'] * 999)
        return f"User clicked at position [{x}, {y}]"
    elif action_type == 'long_press':
        x, y = int(event['x'] * 999), int(event['y'] * 999)
        duration = event.get('duration', 0)
        return f"User long-pressed at position [{x}, {y}] for {duration:.2f} seconds"
    elif action_type == 'swipe':
        start_x, start_y = event.get('start_x', 0), event.get('start_y', 0)
        end_x, end_y = event.get('end_x', 0), event.get('end_y', 0)
        dx = end_x - start_x
        dy = end_y - start_y
        if abs(dx) >= abs(dy):
            direction = 'right' if dx > 0 else 'left'
        else:
            direction = 'down' if dy > 0 else 'up'
        return f"User swiped {direction}"
    elif action_type == 'key_press':
        key = event.get('key_name', 'unknown')
        button = "back" if key == "back" else "home" if key == "home" else "menu" if key == "recents" else key
        return f"User pressed the {button} button"
    else:
        return f"Unknown action: {action_type}"


def format_action_gui_owl_1_5(event: dict, width: int, height: int) -> str:
    """Format an action event for GUI_Owl_1_5 (coordinates normalized by *999).

    GUI_Owl_1_5 uses the mobile_use tool format with actions:
    - click, long_press, swipe (coordinate-based, *999)
    - system_button (Back/Home/Menu/Enter)
    """
    action_type = event.get('type', 'unknown')

    if action_type == 'tap':
        x, y = int(event['x'] * 999), int(event['y'] * 999)
        return f"User clicked at position [{x}, {y}]"
    elif action_type == 'long_press':
        x, y = int(event['x'] * 999), int(event['y'] * 999)
        duration = event.get('duration', 0)
        return f"User long-pressed at position [{x}, {y}] for {duration:.2f} seconds"
    elif action_type == 'swipe':
        x1, y1 = int(event['start_x'] * 999), int(event['start_y'] * 999)
        x2, y2 = int(event['end_x'] * 999), int(event['end_y'] * 999)
        return f"User swiped from [{x1}, {y1}] to [{x2}, {y2}]"
    elif action_type == 'key_press':
        key = event.get('key_name', 'unknown')
        button_map = {'back': 'Back', 'home': 'Home', 'recents': 'Menu', 'enter': 'Enter'}
        button = button_map.get(key, key)
        return f"User pressed the {button} button"
    else:
        return f"Unknown action: {action_type}"


def format_action_ui_venus_1_5(event: dict, width: int, height: int) -> str:
    """Format an action event for UI_Venus_1_5 (absolute coordinates).

    UI_Venus_1_5 uses absolute coordinates and specific action formats:
    - Click(box=(x, y))
    - LongPress(box=(x, y))
    - Drag(start=(x1, y1), end=(x2, y2))
    - Scroll(start=(x1, y1), end=(x2, y2)) or Scroll(direction='...')
    - Type(content='...')
    - Launch(app='...')
    - Wait()
    - Finished(content='...')
    - CallUser(content='...')
    - PressBack(), PressHome(), PressEnter(), PressRecent()
    """
    action_type = event.get('type', 'unknown')

    if action_type == 'tap':
        x, y = int(event.get('x', 0) * 999), int(event.get('y', 0) * 999)
        return f"Click(box=({x}, {y}))"
    elif action_type == 'long_press':
        x, y = int(event.get('x', 0) * 999), int(event.get('y', 0) * 999)
        return f"LongPress(box=({x}, {y}))"
    elif action_type == 'swipe':
        start_x = int(event.get('start_x', 0) * 999)
        start_y = int(event.get('start_y', 0) * 999)
        end_x = int(event.get('end_x', 0) * 999)
        end_y = int(event.get('end_y', 0) * 999)
        dx = end_x - start_x
        dy = end_y - start_y
        # If swipe is small, use direction-based Scroll
        if abs(dx) < 50 and abs(dy) < 50:
            if abs(dx) >= abs(dy):
                direction = 'right' if dx > 0 else 'left'
            else:
                direction = 'down' if dy > 0 else 'up'
            return f"Scroll(direction='{direction}')"
        else:
            return f"Scroll(start=({start_x}, {start_y}), end=({end_x}, {end_y}))"
    elif action_type == 'key_press':
        key = event.get('key_name', 'unknown')
        if key == 'back':
            return "PressBack()"
        elif key == 'home':
            return "PressHome()"
        elif key == 'enter':
            return "PressEnter()"
        elif key == 'recents':
            return "PressRecent()"
        else:
            return f"Unknown key press: {key}"
    else:
        return f"Unknown action: {action_type}"