#!/usr/bin/env python3
import curses
import time
import os
import sys
import itertools
import shutil # For initial terminal width, can be handy

# --- ANSI Escape Codes for Pre-Curses Messages ---
class ConfirmAnsiColors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    ORANGE = '\033[38;5;208m'

# --- Character Iterators (will be initialized in main_curses_wrapper) ---
flame_chars_cycle = None
flame_color_pair_cycle = None
ember_chars_raw_cycle = None
ash_chars_raw_cycle = None

# --- Color Pair Global Definitions ---
PAPER_BORDER_COLOR = None
PAPER_TEXT_COLOR = None
FLAME_RED = None
FLAME_ORANGE = None
FLAME_YELLOW = None
EMBER_RED = None
EMBER_DARK_GREY = None
ASH_DARK_GREY = None
ASH_LIGHT_GREY = None
STATUS_TEXT_COLOR = None
FINAL_MSG_FLAME_COLOR = None
DEFAULT_PAIR = None
DIAGNOSTIC_GREEN_COLOR = None 

_initialized_pairs = {}

def get_flame_char():
    global flame_chars_cycle
    return next(flame_chars_cycle)

def get_flame_color_pair_attr():
    global flame_color_pair_cycle
    return next(flame_color_pair_cycle)

def get_ember_char():
    global ember_chars_raw_cycle
    return next(ember_chars_raw_cycle)

def get_ash_char():
    global ash_chars_raw_cycle
    return next(ash_chars_raw_cycle)

def init_pair_safe(stdscr, pair_number, fg, bg):
    global _initialized_pairs
    if pair_number in _initialized_pairs and _initialized_pairs[pair_number] == (fg,bg):
        return curses.color_pair(pair_number)
    try:
        curses.init_pair(pair_number, fg, bg)
        _initialized_pairs[pair_number] = (fg,bg)
        return curses.color_pair(pair_number)
    except Exception:
        if pair_number not in _initialized_pairs: 
            try: 
                curses.init_pair(pair_number, curses.COLOR_WHITE, curses.COLOR_BLACK)
                _initialized_pairs[pair_number] = (curses.COLOR_WHITE, curses.COLOR_BLACK)
                return curses.color_pair(pair_number)
            except Exception: 
                if 1 in _initialized_pairs and pair_number != 1: return curses.color_pair(1)
        return curses.color_pair(pair_number) 

def init_curses_colors(stdscr):
    global flame_color_pair_cycle, _initialized_pairs
    global PAPER_BORDER_COLOR, PAPER_TEXT_COLOR, FLAME_RED, FLAME_ORANGE, FLAME_YELLOW
    global EMBER_RED, EMBER_DARK_GREY, ASH_DARK_GREY, ASH_LIGHT_GREY
    global STATUS_TEXT_COLOR, FINAL_MSG_FLAME_COLOR, DEFAULT_PAIR, DIAGNOSTIC_GREEN_COLOR

    _initialized_pairs.clear()
    curses.start_color()
    curses.use_default_colors()
    pair_idx = 1

    DEFAULT_PAIR = init_pair_safe(stdscr, pair_idx, curses.COLOR_WHITE, -1); pair_idx += 1
    PAPER_BORDER_COLOR = init_pair_safe(stdscr, pair_idx, curses.COLOR_WHITE, -1); pair_idx += 1
    PAPER_TEXT_COLOR = init_pair_safe(stdscr, pair_idx, curses.COLOR_WHITE, -1) | curses.A_BOLD; pair_idx += 1
    FLAME_RED = init_pair_safe(stdscr, pair_idx, curses.COLOR_RED, -1); pair_idx += 1
    DIAGNOSTIC_GREEN_COLOR = init_pair_safe(stdscr, pair_idx, curses.COLOR_GREEN, -1); pair_idx +=1

    orange_color_val = curses.COLOR_YELLOW
    if curses.COLORS >= 256:
        orange_color_val = 208 
    FLAME_ORANGE = init_pair_safe(stdscr, pair_idx, orange_color_val, -1); pair_idx +=1
    FINAL_MSG_FLAME_COLOR = FLAME_ORANGE

    FLAME_YELLOW = init_pair_safe(stdscr, pair_idx, curses.COLOR_YELLOW, -1); pair_idx += 1
    EMBER_RED = init_pair_safe(stdscr, pair_idx, curses.COLOR_RED, -1); pair_idx += 1

    dark_grey_color_val = curses.COLOR_BLACK 
    if curses.COLORS > 8: 
        dark_grey_color_val = 8 
    EMBER_DARK_GREY = init_pair_safe(stdscr, pair_idx, dark_grey_color_val, -1); pair_idx += 1
    ASH_DARK_GREY = EMBER_DARK_GREY 
    ASH_LIGHT_GREY = PAPER_BORDER_COLOR 
    STATUS_TEXT_COLOR = init_pair_safe(stdscr, pair_idx, curses.COLOR_CYAN, -1) | curses.A_BOLD; pair_idx += 1

    flame_color_pair_cycle = itertools.cycle([FLAME_RED, FLAME_ORANGE, FLAME_YELLOW, FLAME_ORANGE])

def burn_filename_main(stdscr, raw_filename_str_arg):
    curses.curs_set(0)
    stdscr.nodelay(False) 
    init_curses_colors(stdscr)

    term_height, term_width = stdscr.getmaxyx()

    with open("burn_debug.log", "w") as debug_log:
        debug_log.write(f"burn_filename_main started for: {raw_filename_str_arg}\n")
        debug_log.write(f"Terminal: {term_width}x{term_height}, Curses Colors: {curses.COLORS}\n")

    max_name_display_len = term_width - 10 
    display_name = raw_filename_str_arg
    if len(raw_filename_str_arg) > max_name_display_len:
        display_name = raw_filename_str_arg[:max_name_display_len-3] + "..."
    
    name_len = len(display_name)
    animation_width = name_len + 4 
    animation_height = 4 

    with open("burn_debug.log", "a") as debug_log:
        debug_log.write(f"Filename: {raw_filename_str_arg}, display_name: {display_name}, name_len: {name_len}\n")
        debug_log.write(f"animation_width: {animation_width}, animation_height: {animation_height}\n")

    if animation_width >= term_width or animation_height >= term_height:
        stdscr.clear()
        msg = "Terminal too small for animation."
        # Use addstr for messages too, for consistency
        stdscr.addstr(term_height // 2, (term_width - len(msg)) // 2, msg, FLAME_RED if FLAME_RED else DEFAULT_PAIR)
        stdscr.refresh()
        time.sleep(2)
        return

    start_y = (term_height - animation_height) // 2
    start_x = (term_width - animation_width) // 2
    with open("burn_debug.log", "a") as debug_log:
        debug_log.write(f"start_x: {start_x}, start_y: {start_y}\n")

    def clear_animation_area():
        for i in range(animation_height):
            try:
                stdscr.move(start_y + i, start_x)
                stdscr.clrtoeol()
            except curses.error: pass 

    stdscr.clear()
    stdscr.refresh()

    # --- Animation Stages ---
    # Initial State (using addstr for all fixed strings now)
    clear_animation_area()
    stdscr.addstr(start_y, start_x, "┌─" + "─" * name_len + "─┐", PAPER_BORDER_COLOR)
    stdscr.addstr(start_y + 1, start_x, "│ ", PAPER_BORDER_COLOR)
    stdscr.addstr(start_y + 1, start_x + 2, display_name, PAPER_TEXT_COLOR)
    stdscr.addstr(start_y + 1, start_x + 2 + name_len, " │", PAPER_BORDER_COLOR)
    stdscr.addstr(start_y + 2, start_x, "└─" + "─" * name_len + "─┘", PAPER_BORDER_COLOR)
    stdscr.refresh()
    time.sleep(0.6)

    # Ignition (using addstr for single chars)
    try:
        stdscr.addstr(start_y + 2, start_x + 1 + name_len, '.', FLAME_YELLOW | curses.A_BOLD)
        stdscr.addstr(start_y + 3, start_x + 2 + name_len, "'", FLAME_YELLOW | curses.A_BOLD)
        stdscr.refresh()
        time.sleep(0.25)
    except curses.error: pass

    try:
        stdscr.addstr(start_y + 2, start_x + 1 + name_len, get_flame_char(), get_flame_color_pair_attr())
        stdscr.addstr(start_y + 3, start_x + 1 + name_len, " " ) 
        stdscr.addstr(start_y + 3, start_x + 2 + name_len, get_flame_char(), get_flame_color_pair_attr())
        stdscr.refresh()
        time.sleep(0.18)
    except curses.error: pass

    # File Name & Border Consumption (using addstr for dynamic chars)
    for i in range(1, name_len + 1):
        clear_animation_area()
        stdscr.addstr(start_y, start_x, "┌─" + "─" * name_len + "─┐", PAPER_BORDER_COLOR)
        
        text_part = display_name[:-i]
        stdscr.addstr(start_y + 1, start_x, "│ ", PAPER_BORDER_COLOR)
        stdscr.addstr(start_y + 1, start_x + 2, text_part, PAPER_TEXT_COLOR)
        current_x_offset = start_x + 2 + len(text_part)
        for _ in range(i): 
            if current_x_offset < start_x + 2 + name_len:
                try: stdscr.addstr(start_y + 1, current_x_offset, get_flame_char(), get_flame_color_pair_attr())
                except curses.error: pass
                current_x_offset += 1
        stdscr.addstr(start_y + 1, start_x + 2 + name_len, " │", PAPER_BORDER_COLOR)

        border_consumed_len = min(name_len, i + name_len // 4) 
        border_solid_part_len = name_len - border_consumed_len
        stdscr.addstr(start_y + 2, start_x, "└─", PAPER_BORDER_COLOR)
        stdscr.addstr(start_y + 2, start_x + 2, "─" * border_solid_part_len, PAPER_BORDER_COLOR)
        current_x_offset = start_x + 2 + border_solid_part_len
        for _ in range(border_consumed_len):
            if current_x_offset < start_x + 2 + name_len:
                try: stdscr.addstr(start_y + 2, current_x_offset, get_flame_char(), get_flame_color_pair_attr())
                except curses.error: pass
                current_x_offset +=1
        stdscr.addstr(start_y + 2, start_x + 2 + name_len, "─┘", PAPER_BORDER_COLOR)
        
        flames_below_count = min(name_len // 2 + 2, i + 1)
        flames_start_x_adj = start_x + 2 + (name_len - flames_below_count) 
        for k_flame in range(flames_below_count):
            try: stdscr.addstr(start_y + 3, flames_start_x_adj + k_flame, get_flame_char(), get_flame_color_pair_attr())
            except curses.error: pass
        
        stdscr.refresh()
        sleep_duration = 0.18
        if i > 0 and i < name_len and i % (max(1, name_len // 5 if name_len > 5 else 1)) == 0:
            sleep_duration = 0.30 
        time.sleep(sleep_duration)

    # Full Burn (using addstr)
    for i in range(6): 
        clear_animation_area()
        offset_l0 = i % 3
        for k in range(name_len + 1 + offset_l0): 
            try: stdscr.addstr(start_y + 0, start_x + 1 + k, get_flame_char(), get_flame_color_pair_attr())
            except curses.error: pass
        offset_l1 = i % 2
        for k in range(name_len + 3 - offset_l1): 
            try: stdscr.addstr(start_y + 1, start_x + k, get_flame_char(), get_flame_color_pair_attr())
            except curses.error: pass
        for k_l2 in range(name_len + 2 + offset_l1): 
            try: stdscr.addstr(start_y + 2, start_x + 1 + k_l2, get_flame_char(), get_flame_color_pair_attr())
            except curses.error: pass
        flames_l3_start = start_x + name_len // 4
        for k_l3 in range(name_len // 2 + 1 - offset_l0): 
            try: stdscr.addstr(start_y + 3, flames_l3_start + k_l3, get_flame_char(), get_flame_color_pair_attr())
            except curses.error: pass
        stdscr.refresh()
        time.sleep(0.18)

    # Turning to Embers (using addstr)
    for i in range(4):
        clear_animation_area()
        ember_line_width = name_len + 2 
        for y_idx, anim_line_y in enumerate([start_y + 1, start_y + 2]):
            ember_x_start_pos = start_x + 1 
            for k in range(ember_line_width):
                is_red_ember = (k % (4-i+1) <=1) or ( (i < 2) and (k % 2 == 0) )
                ember_char_val = get_ember_char()
                ember_color_val = EMBER_RED if is_red_ember else EMBER_DARK_GREY
                try: stdscr.addstr(anim_line_y, ember_x_start_pos + k, ember_char_val, ember_color_val)
                except curses.error: pass
        try: 
            stdscr.addstr(start_y + 0, start_x + animation_width // 2, get_ember_char(), EMBER_DARK_GREY)
            stdscr.addstr(start_y + 3, start_x + animation_width // 2 -1, get_ember_char(), EMBER_DARK_GREY)
            stdscr.addstr(start_y + 3, start_x + animation_width // 2 +1, get_ember_char(), EMBER_DARK_GREY)
        except curses.error: pass
        stdscr.refresh()
        time.sleep(0.35 if i > 1 else 0.25)

    # Ashes
    active_paper_width = name_len + 2 
    with open("burn_debug.log", "a") as debug_log:
        debug_log.write(f"Ash phase: active_paper_width: {active_paper_width}\n")

    for i in range(5): 
        clear_animation_area()

        if i == 0: 
            ash_draw_start_x_initial = start_x + 1
            ash_width_initial = active_paper_width

            with open("burn_debug.log", "a") as debug_log:
                debug_log.write(f"Ash i=0: ash_width_initial: {ash_width_initial}, ash_draw_start_x_initial: {ash_draw_start_x_initial}\n")

            if ash_width_initial <= 0:
                with open("burn_debug.log", "a") as debug_log:
                    debug_log.write("Ash i=0: ash_width_initial is <=0, skipping draw loop.\n")
                continue

            for anim_line_y in [start_y + 1, start_y + 2]:
                for k in range(ash_width_initial):
                    draw_x = ash_draw_start_x_initial + k
                    char_to_draw = get_ash_char()
                    color_to_use = ASH_DARK_GREY
                    
                    if k == ash_width_initial - 1: 
                        with open("burn_debug.log", "a") as debug_log:
                            debug_log.write(f"  Ash i=0, line Y={anim_line_y-start_y}: Attempting LAST ash char '{char_to_draw}' with addstr at screen_x={draw_x} (k={k})\n")
                    
                    if draw_x < start_x + animation_width: 
                        try:
                            # MODIFICATION: Use addstr
                            stdscr.addstr(anim_line_y, draw_x, char_to_draw, color_to_use)
                        except curses.error as e:
                            with open("burn_debug.log", "a") as debug_log:
                                debug_log.write(f"  Ash i=0, line Y={anim_line_y-start_y}: curses.error on addstr for ash char at screen_x={draw_x}: {e}. Clearing cell.\n")
                            try:
                                # MODIFICATION: Use addstr for space
                                stdscr.addstr(anim_line_y, draw_x, ' ', DEFAULT_PAIR if DEFAULT_PAIR else curses.A_NORMAL)
                            except curses.error as e_space:
                                with open("burn_debug.log", "a") as debug_log:
                                    debug_log.write(f"  Ash i=0, line Y={anim_line_y-start_y}: curses.error on addstr for clearing cell at screen_x={draw_x}: {e_space}\n")
                    else: 
                        with open("burn_debug.log", "a") as debug_log:
                            debug_log.write(f"  Ash i=0, line Y={anim_line_y-start_y}: SKIPPED ash char at screen_x={draw_x} (draw_x >= start_x + animation_width)\n")
        else: 
            current_ash_width_calculated = max(0, active_paper_width - i * 2) 
            if current_ash_width_calculated <=0: continue

            ash_centering_offset = (active_paper_width - current_ash_width_calculated) // 2
            ash_draw_start_x_shrinking = start_x + 1 + ash_centering_offset
            for anim_line_y in [start_y + 1, start_y + 2]:
                for k in range(current_ash_width_calculated):
                    draw_x = ash_draw_start_x_shrinking + k
                    if draw_x < start_x + animation_width:
                        try:
                            # MODIFICATION: Use addstr
                            stdscr.addstr(anim_line_y, draw_x, get_ash_char(), ASH_DARK_GREY)
                        except curses.error:
                            try:
                                # MODIFICATION: Use addstr for space
                                stdscr.addstr(anim_line_y, draw_x, ' ', DEFAULT_PAIR if DEFAULT_PAIR else curses.A_NORMAL)
                            except curses.error:
                                pass 
        
        ash_density_l3_scatter = max(0, (name_len // 2 + 1) - i)
        if ash_density_l3_scatter > 0:
            ash_l3_centering_offset = ((name_len // 2 + 1) - ash_density_l3_scatter) // 2
            ash_draw_start_x_l3 = start_x + (animation_width // 2) - ((name_len // 2 + 1) // 2) + ash_l3_centering_offset
            for k in range(ash_density_l3_scatter):
                draw_x_l3 = ash_draw_start_x_l3 + k
                if draw_x_l3 >= start_x and draw_x_l3 < start_x + animation_width:
                    try: 
                        # MODIFICATION: Use addstr
                        stdscr.addstr(start_y + 3, draw_x_l3, get_ash_char(), ASH_LIGHT_GREY)
                    except curses.error: pass

        if ash_density_l3_scatter > 0 and i < 4 : 
            draw_x_dot = start_x + animation_width // 2 
            if draw_x_dot >= start_x and draw_x_dot < start_x + animation_width:
                try: 
                    # MODIFICATION: Use addstr
                    stdscr.addstr(start_y + 3, draw_x_dot , '.', ASH_DARK_GREY)
                except curses.error: pass
        
        stdscr.refresh()
        time.sleep(0.35)

    # Fading Away & Final Message
    clear_animation_area() 
    stdscr.refresh()
    time.sleep(0.30)
    stdscr.clear() 
    final_message1_raw = f"🔥 '{raw_filename_str_arg}' has been turned to digital ash. 🔥"
    final_message2_raw = "May your worries dissipate with it."
    msg1_y = term_height // 2 - 1
    msg2_y = term_height // 2
    msg1_x = (term_width - len(final_message1_raw)) // 2
    msg2_x = (term_width - len(final_message2_raw)) // 2
    msg_color = FINAL_MSG_FLAME_COLOR if FINAL_MSG_FLAME_COLOR else DEFAULT_PAIR
    try:
        stdscr.addstr(msg1_y, max(0, msg1_x), final_message1_raw, msg_color | curses.A_BOLD)
        stdscr.addstr(msg2_y, max(0, msg2_x), final_message2_raw, PAPER_TEXT_COLOR if PAPER_TEXT_COLOR else DEFAULT_PAIR)
    except curses.error: pass 
    stdscr.refresh()
    stdscr.nodelay(False) 
    stdscr.getch() 

def main_curses_wrapper():
    global flame_chars_cycle, ember_chars_raw_cycle, ash_chars_raw_cycle, _initialized_pairs

    if len(sys.argv) < 2:
        print(f"{ConfirmAnsiColors.RED}Usage: python {os.path.basename(__file__)} <file_to_burn>{ConfirmAnsiColors.RESET}")
        sys.exit(1)

    file_to_burn_path = sys.argv[1]
    file_to_burn_basename = os.path.basename(file_to_burn_path)

    if not os.path.exists(file_to_burn_path):
        print(f"{ConfirmAnsiColors.RED}Error: File '{file_to_burn_path}' not found.{ConfirmAnsiColors.RESET}")
        sys.exit(1)
    if not os.path.isfile(file_to_burn_path):
        print(f"{ConfirmAnsiColors.RED}Error: '{file_to_burn_path}' is not a file.{ConfirmAnsiColors.RESET}")
        sys.exit(1)

    print(f"You are about to digitally incinerate: {ConfirmAnsiColors.BOLD}{file_to_burn_basename}{ConfirmAnsiColors.RESET}")
    confirm = input(f"Are you sure you want to proceed? ({ConfirmAnsiColors.GREEN}yes{ConfirmAnsiColors.RESET}/{ConfirmAnsiColors.RED}no{ConfirmAnsiColors.RESET}): ").lower()

    if confirm not in ['yes', 'y']:
        print("Incineration cancelled.")
        sys.exit(0)

    flame_chars_cycle = itertools.cycle(["🔥", "*", "^", "✸", "✺", "✹", "✵", "#", "@", "W", "V", "M", "~"])
    ember_chars_raw_cycle = itertools.cycle(['∴', '∵', '.', '*', '·', '°', ':'])
    ash_chars_raw_cycle = itertools.cycle(['.', '`', ' ', ':', '.', ' ', '~', '-']) 
    _initialized_pairs = {} 

    file_deleted_successfully = False
    animation_completed_without_curses_error = False
    try:
        curses.wrapper(burn_filename_main, file_to_burn_basename)
        animation_completed_without_curses_error = True 

        try:
            os.remove(file_to_burn_path)
            file_deleted_successfully = True
        except OSError as e:
            print(f"{ConfirmAnsiColors.RED}\nAnimation complete, but failed to delete file '{file_to_burn_basename}': {e}{ConfirmAnsiColors.RESET}")

    except curses.error as e:
        print(f"{ConfirmAnsiColors.RED}\nA curses error occurred during animation: {e}{ConfirmAnsiColors.RESET}")
        print("The terminal might be in an unusual state. Try 'reset'.")
    except Exception as e:
        print(f"{ConfirmAnsiColors.RED}\nAn unexpected error occurred: {e}{ConfirmAnsiColors.RESET}")
    finally:
        sys.stdout.write("\033[?25h") 
        sys.stdout.flush()

        if animation_completed_without_curses_error:
            if file_deleted_successfully:
                print(f"\n{ConfirmAnsiColors.GREEN}'{file_to_burn_basename}' has been deleted.{ConfirmAnsiColors.RESET}")
            elif os.path.exists(file_to_burn_path): 
                 print(f"\n{ConfirmAnsiColors.ORANGE}File '{file_to_burn_basename}' was NOT deleted (delete operation failed or was skipped after animation).{ConfirmAnsiColors.RESET}")
        else: 
            print(f"\n{ConfirmAnsiColors.ORANGE}Animation did not complete successfully. File '{file_to_burn_basename}' was NOT deleted.{ConfirmAnsiColors.RESET}")

if __name__ == "__main__":
    main_curses_wrapper()
