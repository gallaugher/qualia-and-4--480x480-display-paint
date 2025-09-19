# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
Optimized painting demo with smooth lines and fast rectangle-based clear
"""

import displayio
import time
import terminalio
from adafruit_display_text import label
from adafruit_qualia.graphics import Displays, Graphics

graphics = Graphics(Displays.SQUARE40, default_bg=None, auto_refresh=False)

if graphics.touch is None:
    raise RuntimeError("This example requires a touch screen.")

# Configuration - assuming 720x720 display
palette_width = 160
drawing_area_width = graphics.display.width - palette_width  # 560 pixels
drawing_area_height = graphics.display.height  # 720 pixels

# 9 sections: 7 colors + clear + size buttons
section_height = graphics.display.height // 9
brush_sizes = [1, 3, 6, 9, 12]
current_brush_index = 2  # Start with size 6
pixel_size = brush_sizes[current_brush_index]

# Create the fast clear rectangle once
clear_rectangle = None


def draw_line(bitmap, x1, y1, x2, y2, color, size):
    """Draw a line between two points - SIMPLE version for speed"""
    # Simple line drawing - just interpolate between points
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    steps = max(dx, dy)

    if steps == 0:
        # Single point
        draw_brush(bitmap, x1, y1, color, size)
        return

    for i in range(steps + 1):
        t = i / steps
        x = int(x1 + t * (x2 - x1))
        y = int(y1 + t * (y2 - y1))
        draw_brush(bitmap, x, y, color, size)


def draw_brush(bitmap, x, y, color, size):
    """Draw a square brush at the specified position - FAST version"""
    half_size = size // 2
    for i in range(-half_size, half_size + 1):
        for j in range(-half_size, half_size + 1):
            x_pixel = x + i
            y_pixel = y + j
            if (0 <= x_pixel < graphics.display.width and
                    0 <= y_pixel < graphics.display.height):
                bitmap[x_pixel, y_pixel] = color


def create_bitmap_and_palette():
    """Create bitmap with 7 colors + black"""
    bitmap = displayio.Bitmap(graphics.display.width, graphics.display.height, 65535)

    # Fill background with pure black
    for x in range(graphics.display.width):
        for y in range(graphics.display.height):
            bitmap[x, y] = 0x0000

    # Create 7 color bands + black band
    for i in range(palette_width):
        color_index = i * 255 // palette_width
        rgb565 = displayio.ColorConverter().convert(color_index | color_index << 8 | color_index << 16)
        r_mask = 0xF800
        g_mask = 0x07E0
        b_mask = 0x001F

        # 8 color sections (removed gray, added black)
        for j in range(section_height):
            bitmap[i, j + section_height * 0] = rgb565 & b_mask  # Blue
            bitmap[i, j + section_height * 1] = rgb565 & (b_mask | g_mask)  # Cyan
            bitmap[i, j + section_height * 2] = rgb565 & g_mask  # Green
            bitmap[i, j + section_height * 3] = rgb565 & (r_mask | g_mask)  # Yellow
            bitmap[i, j + section_height * 4] = rgb565 & r_mask  # Red
            bitmap[i, j + section_height * 5] = rgb565 & (r_mask | b_mask)  # Magenta
            bitmap[i, j + section_height * 6] = rgb565  # White (faded to full)
            bitmap[i, j + section_height * 7] = 0x0000  # Black

    return bitmap


def setup_fast_clear():
    """Set up the fast clear rectangle once"""
    global clear_rectangle

    # Create black rectangle that covers only the drawing area
    clear_bg = displayio.Bitmap(drawing_area_width, drawing_area_height, 1)
    clear_palette = displayio.Palette(1)
    clear_palette[0] = 0x0000  # Black

    clear_rectangle = displayio.TileGrid(
        clear_bg,
        pixel_shader=clear_palette,
        x=palette_width,  # Start after palette
        y=0
    )


def create_ui_elements():
    """Create UI elements - reuse existing bitmap areas"""
    ui_group = displayio.Group()

    # Clear button area (section 7) - overlay on existing bitmap
    clear_y = section_height * 7
    clear_bg = displayio.Bitmap(palette_width, section_height, 1)
    clear_palette = displayio.Palette(1)
    clear_palette[0] = 0x333333  # Dark gray
    clear_tile = displayio.TileGrid(clear_bg, pixel_shader=clear_palette, x=0, y=clear_y)
    ui_group.append(clear_tile)

    clear_label = label.Label(
        terminalio.FONT,
        text="CLEAR",
        color=0xFFFFFF,
        scale=3
    )
    clear_label.anchor_point = (0.5, 0.5)
    clear_label.anchored_position = (palette_width // 2, clear_y + section_height // 2)
    ui_group.append(clear_label)

    # Size button area (section 8)
    size_y = section_height * 8
    size_bg = displayio.Bitmap(palette_width, section_height, 1)
    size_palette = displayio.Palette(1)
    size_palette[0] = 0x444444  # Different dark gray
    size_tile = displayio.TileGrid(size_bg, pixel_shader=size_palette, x=0, y=size_y)
    ui_group.append(size_tile)

    brush_label = label.Label(
        terminalio.FONT,
        text=f"SIZE {brush_sizes[current_brush_index]}",
        color=0xFFFFFF,
        scale=3
    )
    brush_label.anchor_point = (0.5, 0.5)
    brush_label.anchored_position = (palette_width // 2, size_y + section_height // 2)
    ui_group.append(brush_label)

    return ui_group, brush_label


# Create initial setup with visual progress
print("Setting up fast painter...")

# Show progress on screen during bitmap creation
graphics.display.auto_refresh = True
progress_group = displayio.Group()
progress_bg = displayio.Bitmap(graphics.display.width, graphics.display.height, 1)
progress_palette = displayio.Palette(1)
progress_palette[0] = 0x000088  # Dark blue
progress_tile = displayio.TileGrid(progress_bg, pixel_shader=progress_palette)
progress_group.append(progress_tile)

progress_label = label.Label(
    terminalio.FONT,
    text="Creating interface...\nThis may take about a minute.\nPlease be patient.",
    color=0xFFFFFF,
    scale=2,
    x=graphics.display.width // 2,
    y=graphics.display.height // 2
)
progress_label.anchor_point = (0.5, 0.5)
progress_label.anchored_position = (graphics.display.width // 2, graphics.display.height // 2)
progress_group.append(progress_label)

graphics.display.root_group = progress_group
time.sleep(0.5)  # Let user see the message

print("Creating bitmap...")
progress_label.text = "Building color palette...\nThis may take up to a minute.\nPlease be patient."
bitmap = create_bitmap_and_palette()

print("Setting up UI...")
progress_label.text = "Creating buttons..."
setup_fast_clear()
ui_group, brush_label = create_ui_elements()

main_group = displayio.Group()
tile_grid = displayio.TileGrid(
    bitmap,
    pixel_shader=displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565),
)

main_group.append(tile_grid)
main_group.append(ui_group)
graphics.display.root_group = main_group

# Drawing state - smooth line drawing with better button debouncing
current_color = displayio.ColorConverter().convert(0xFFFFFF)
last_touch_time = 0
touch_delay = 0.005  # Fast response for drawing
last_draw_pos = None  # For smooth line drawing
is_drawing = False

# Better button debouncing
size_button_pressed = False
size_button_last_change = 0
clear_button_pressed = False
clear_button_last_change = 0
button_debounce_time = 0.5  # Half second between button presses

print("Optimized Touch Painter Ready!")
print(f"Display: {graphics.display.width}x{graphics.display.height}")
print(f"Palette: {palette_width}px wide")
print(f"Drawing area: {drawing_area_width}x{drawing_area_height}px")

graphics.display.auto_refresh = True

while True:
    current_time = time.monotonic()

    if graphics.touch.touched:
        if (current_time - last_touch_time) > touch_delay:
            try:
                for touch in graphics.touch.touches:
                    x = touch["x"]
                    y = touch["y"]

                    if not 0 <= x < graphics.display.width or not 0 <= y < graphics.display.height:
                        continue

                    # Left column interactions
                    if x < palette_width:
                        section = y // section_height

                        if section == 7:  # Clear button
                            # State-based debouncing for clear button
                            if not clear_button_pressed:
                                if (current_time - clear_button_last_change) > button_debounce_time:
                                    print("Actually clearing bitmap...")

                                    # Actually clear the bitmap pixels (not just overlay)
                                    for x_clear in range(palette_width, graphics.display.width):
                                        for y_clear in range(graphics.display.height):
                                            bitmap[x_clear, y_clear] = 0x0000

                                    print("Cleared!")
                                    clear_button_pressed = True
                                    clear_button_last_change = current_time
                                    last_draw_pos = None
                                    is_drawing = False

                        elif section == 8:  # Size button
                            # State-based debouncing for size button
                            if not size_button_pressed:
                                if (current_time - size_button_last_change) > button_debounce_time:
                                    current_brush_index = (current_brush_index + 1) % len(brush_sizes)
                                    pixel_size = brush_sizes[current_brush_index]
                                    brush_label.text = f"SIZE {pixel_size}"
                                    print(f"Brush size: {pixel_size}")

                                    size_button_pressed = True
                                    size_button_last_change = current_time
                                    last_draw_pos = None
                                    is_drawing = False

                        elif section < 7:  # Color selection (0-6)
                            current_color = bitmap[x, y]
                            color_names = ["Blue", "Cyan", "Green", "Yellow", "Red", "Magenta", "White", "Black"]
                            if section < len(color_names):
                                print(f"Color: {color_names[section]} ({hex(current_color)})")
                            last_draw_pos = None
                            is_drawing = False

                    # Drawing area - smooth line drawing
                    elif x >= palette_width:
                        if is_drawing and last_draw_pos is not None:
                            # Draw smooth line from last position to current position
                            draw_line(bitmap, last_draw_pos[0], last_draw_pos[1], x, y, current_color, pixel_size)
                        else:
                            # First touch - just draw at current position
                            draw_brush(bitmap, x, y, current_color, pixel_size)

                        last_draw_pos = (x, y)
                        is_drawing = True

                    last_touch_time = current_time

            except RuntimeError:
                pass
    else:
        # Touch released - reset drawing state and button states
        if is_drawing:
            last_draw_pos = None
            is_drawing = False

        # Reset button states when touch is released
        size_button_pressed = False
        clear_button_pressed = False 