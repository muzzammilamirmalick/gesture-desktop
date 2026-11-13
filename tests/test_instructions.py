import config
import controller
import instructions
from menu import LABELS


def test_every_menu_item_has_a_label_and_help():
    for item in config.MENU_ITEMS:
        assert item in LABELS
        assert instructions.MENU_HELP.get(item)


def test_every_menu_item_does_something():
    for item in config.MENU_ITEMS:
        assert item in controller.INSTANT_ITEMS or item in controller.MODE_ITEMS


def test_instant_items_have_shortcuts_on_both_systems():
    for item in controller.INSTANT_ITEMS:
        assert item in config.SHORTCUTS["windows"]
        assert item in config.SHORTCUTS["mac"]


def test_help_panel_lists_the_two_gestures_and_the_menu():
    sections = dict(instructions.help_sections())
    names = [name for name, _ in sections["Always on"]]
    assert names == ["Point", "Pinch", "Open palm, hold"]
    assert len(sections["In the menu"]) >= len(config.MENU_ITEMS)


def test_unimportant_hand_shapes_just_say_hand():
    assert instructions.hand_name("thumbs_up") == "hand"
    assert instructions.hand_name("point") == "point"
