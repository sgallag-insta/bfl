#!/usr/bin/env python3
import curses
import time
import os
import sys
import itertools
import argparse

# --- ANSI Escape Codes for Pre-Curses Messages ---
class ConfirmAnsiColors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    ORANGE = '\033[38;5;208m'

# --- Animation Constants ---
BOX_HLINE = "─"
BOX_VLINE = "│"
BOX_TL = "┌"
BOX_TR = "┐"
BOX_BL = "└"
BOX_BR = "┘"

ANIMATION_BOX_PADDING_X = 1 
ANIMATION_BOX_BORDER_THICKNESS = 1
ANIMATION_BOX_TOTAL_HORIZONTAL_OVERHEAD = (ANIMATION_BOX_PADDING_X + ANIMATION_BOX_BORDER_THICKNESS) * 2
ANIMATION_BOX_HEIGHT = 4

FILENAME_TRUNCATION_SUFFIX = "..."
FILENAME_TRUNCATION_RESERVE = len(FILENAME_TRUNCATION_SUFFIX) + ANIMATION_BOX_TOTAL_HORIZONTAL_OVERHEAD + 2

FLAME_CHARS = ["&", "*", "^", "✸", "✺", "✹", "✵", "#", "@", "W", "V", "M", "~"]
EMBER_CHARS = ['∴', '∵', '.', '*', '·', '°', ':']
ASH_CHARS = ['.', '`', ' ', ':', '.', ' ', '~', '-']


class CursesAnimator:
    def __init__(self, stdscr, filename_to_burn):
        self.stdscr = stdscr
        self.raw_filename_str_arg = filename_to_burn
        self._initialized_pairs = {}

        self.flame_chars_cycle = itertools.cycle(FLAME_CHARS)
        self.ember_chars_cycle = itertools.cycle(EMBER_CHARS)
        self.ash_chars_cycle = itertools.cycle(ASH_CHARS)
        self.flame_color_pair_cycle = None

        self.DEFAULT_PAIR = None
        self.PAPER_BORDER_COLOR = None
        self.PAPER_TEXT_COLOR = None
        self.FLAME_RED = None
        self.FLAME_ORANGE = None
        self.FLAME_YELLOW = None
        self.EMBER_RED = None
        self.EMBER_DARK_GREY = None
        self.ASH_DARK_GREY = None
        self.ASH_LIGHT_GREY = None
        self.STATUS_TEXT_COLOR = None
        self.FINAL_MSG_FLAME_COLOR = None

        self.term_height = 0
        self.term_width = 0
        self.display_name = ""
        self.name_len = 0
        self.animation_width = 0
        self.animation_height = ANIMATION_BOX_HEIGHT
        self.start_y = 0
        self.start_x = 0

    def _get_flame_char(self): return next(self.flame_chars_cycle)
    def _get_flame_color_attr(self): return next(self.flame_color_pair_cycle)
    def _get_ember_char(self): return next(self.ember_chars_cycle)
    def _get_ash_char(self): return next(self.ash_chars_cycle)

    def _safe_init_pair(self, pair_number, fg, bg):
        if self._initialized_pairs.get(pair_number) == (fg, bg):
            return curses.color_pair(pair_number)
        try:
            curses.init_pair(pair_number, fg, bg)
            self._initialized_pairs[pair_number] = (fg, bg)
            return curses.color_pair(pair_number)
        except curses.error:
            return self.DEFAULT_PAIR

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        pair_idx = 1

        try:
            curses.init_pair(pair_idx, curses.COLOR_WHITE, -1)
            self._initialized_pairs[pair_idx] = (curses.COLOR_WHITE, -1)
            self.DEFAULT_PAIR = curses.color_pair(pair_idx)
        except curses.error:
            self.DEFAULT_PAIR = curses.A_NORMAL
        pair_idx += 1

        self.PAPER_BORDER_COLOR = self._safe_init_pair(pair_idx, curses.COLOR_WHITE, -1); pair_idx += 1
        self.PAPER_TEXT_COLOR = self._safe_init_pair(pair_idx, curses.COLOR_WHITE, -1) | curses.A_BOLD; pair_idx += 1
        self.FLAME_RED = self._safe_init_pair(pair_idx, curses.COLOR_RED, -1); pair_idx += 1
        
        orange_color_val = curses.COLOR_YELLOW if curses.COLORS < 256 else 208
        self.FLAME_ORANGE = self._safe_init_pair(pair_idx, orange_color_val, -1); pair_idx +=1
        self.FINAL_MSG_FLAME_COLOR = self.FLAME_ORANGE

        self.FLAME_YELLOW = self._safe_init_pair(pair_idx, curses.COLOR_YELLOW, -1); pair_idx += 1
        self.EMBER_RED = self._safe_init_pair(pair_idx, curses.COLOR_RED, -1); pair_idx += 1

        dark_grey_color_val = curses.COLOR_BLACK if curses.COLORS <= 8 else 8
        self.EMBER_DARK_GREY = self._safe_init_pair(pair_idx, dark_grey_color_val, -1); pair_idx += 1
        self.ASH_DARK_GREY = self.EMBER_DARK_GREY
        self.ASH_LIGHT_GREY = self.PAPER_BORDER_COLOR
        self.STATUS_TEXT_COLOR = self._safe_init_pair(pair_idx, curses.COLOR_CYAN, -1) | curses.A_BOLD; pair_idx += 1
        
        self.flame_color_pair_cycle = itertools.cycle([
            self.FLAME_RED, self.FLAME_ORANGE, self.FLAME_YELLOW, self.FLAME_ORANGE
        ])

    def _safe_addstr(self, y, x, text, attr=None):
        # --- Add this debugging block ---
        # Calculate the first X coordinate that is *past* the paper's right edge
        paper_right_edge_exclusive_x = self.start_x + self.animation_width 
        
        if x >= paper_right_edge_exclusive_x:
            # This write is AT or BEYOND the calculated right border of the animation box
            try:
                with open("bfl_debug_overflow.log", "a") as debug_log:
                    debug_log.write(
                        f"Timestamp: {time.time():.2f}, " 
                        f"Overflow attempt: y={y} (rel: {y - self.start_y}), x={x}, text='{text[0]}', "
                        f"paper_box_x_range=[{self.start_x}-{paper_right_edge_exclusive_x -1}], "
                        f"animation_width={self.animation_width}, name_len={self.name_len}\n"
                    )
            except Exception: 
                pass # Avoid crashing the animation due to logging issues
            # To strictly prevent drawing past the defined paper edge during debug:
            # return 
        # --- End of debugging block ---

        if attr is None:
            attr = self.DEFAULT_PAIR
        
        try:
            if 0 <= y < self.term_height and 0 <= x < self.term_width: # Terminal boundary check
                max_len_for_pos = self.term_width - x
                safe_text = text[:max_len_for_pos]
                if safe_text:
                     self.stdscr.addstr(y, x, safe_text, attr)
        except curses.error:
            pass 

    def _clear_animation_area(self):
        for i in range(self.animation_height):
            line_y = self.start_y + i
            if 0 <= line_y < self.term_height:
                self._safe_addstr(line_y, self.start_x, ' ' * self.animation_width, self.DEFAULT_PAIR)

    def _setup_dimensions(self):
        self.term_height, self.term_width = self.stdscr.getmaxyx()

        max_name_display_len = self.term_width - FILENAME_TRUNCATION_RESERVE
        if len(self.raw_filename_str_arg) > max_name_display_len:
            self.display_name = self.raw_filename_str_arg[:max_name_display_len - len(FILENAME_TRUNCATION_SUFFIX)] + FILENAME_TRUNCATION_SUFFIX
        else:
            self.display_name = self.raw_filename_str_arg
        
        self.name_len = len(self.display_name)
        self.animation_width = (ANIMATION_BOX_BORDER_THICKNESS * 2) + \
                               (ANIMATION_BOX_PADDING_X * 2) + \
                               self.name_len

        if self.animation_width >= self.term_width or self.animation_height >= self.term_height:
            self.stdscr.clear()
            msg = "Terminal too small for animation."
            color = self.FLAME_RED if self.FLAME_RED else self.DEFAULT_PAIR
            self._safe_addstr(self.term_height // 2, (self.term_width - len(msg)) // 2, msg, color)
            self.stdscr.refresh()
            time.sleep(2)
            return False

        self.start_y = (self.term_height - self.animation_height) // 2
        self.start_x = (self.term_width - self.animation_width) // 2
        return True

    def _draw_initial_paper(self):
        self._clear_animation_area()
        self._safe_addstr(self.start_y, self.start_x,
                          f"{BOX_TL}{BOX_HLINE * (self.name_len + ANIMATION_BOX_PADDING_X * 2)}{BOX_TR}",
                          self.PAPER_BORDER_COLOR)
        self._safe_addstr(self.start_y + 1, self.start_x, BOX_VLINE, self.PAPER_BORDER_COLOR)
        self._safe_addstr(self.start_y + 1, self.start_x + ANIMATION_BOX_BORDER_THICKNESS + ANIMATION_BOX_PADDING_X,
                          self.display_name, self.PAPER_TEXT_COLOR)
        self._safe_addstr(self.start_y + 1, self.start_x + self.animation_width - ANIMATION_BOX_BORDER_THICKNESS,
                          BOX_VLINE, self.PAPER_BORDER_COLOR)
        self._safe_addstr(self.start_y + 2, self.start_x,
                          f"{BOX_BL}{BOX_HLINE * (self.name_len + ANIMATION_BOX_PADDING_X * 2)}{BOX_BR}",
                          self.PAPER_BORDER_COLOR)
        self.stdscr.refresh()
        time.sleep(0.6)

    def _animate_ignition(self):
        ignition_point_x = self.start_x + self.animation_width - ANIMATION_BOX_BORDER_THICKNESS - ANIMATION_BOX_PADDING_X
        self._safe_addstr(self.start_y + 2, ignition_point_x, '.', self.FLAME_YELLOW | curses.A_BOLD)
        self._safe_addstr(self.start_y + 3, ignition_point_x + 1, "'", self.FLAME_YELLOW | curses.A_BOLD)
        self.stdscr.refresh()
        time.sleep(0.25)

        self._safe_addstr(self.start_y + 2, ignition_point_x, self._get_flame_char(), self._get_flame_color_attr())
        self._safe_addstr(self.start_y + 3, ignition_point_x, " ") 
        self._safe_addstr(self.start_y + 3, ignition_point_x + 1, self._get_flame_char(), self._get_flame_color_attr())
        self.stdscr.refresh()
        time.sleep(0.18)

    def _animate_consumption(self):
        name_draw_start_x = self.start_x + ANIMATION_BOX_BORDER_THICKNESS + ANIMATION_BOX_PADDING_X

        for i in range(1, self.name_len + 1): 
            self._clear_animation_area()
            
            self._safe_addstr(self.start_y, self.start_x,
                              f"{BOX_TL}{BOX_HLINE * (self.name_len + ANIMATION_BOX_PADDING_X * 2)}{BOX_TR}",
                              self.PAPER_BORDER_COLOR)
            self._safe_addstr(self.start_y + 1, self.start_x, BOX_VLINE, self.PAPER_BORDER_COLOR)

            text_part_unburnt = self.display_name[:-i]
            self._safe_addstr(self.start_y + 1, name_draw_start_x, text_part_unburnt, self.PAPER_TEXT_COLOR)
            
            flame_start_x_on_name_text = name_draw_start_x + len(text_part_unburnt)
            for char_idx in range(i):
                self._safe_addstr(self.start_y + 1, flame_start_x_on_name_text + char_idx,
                                  self._get_flame_char(), self._get_flame_color_attr())

            self._safe_addstr(self.start_y + 1, self.start_x + self.animation_width - ANIMATION_BOX_BORDER_THICKNESS,
                              BOX_VLINE, self.PAPER_BORDER_COLOR)

            # --- BOTTOM BORDER HANDLING (Segmented approach) ---
            self._safe_addstr(self.start_y + 2, self.start_x,
                              f"{BOX_BL}{BOX_HLINE * ANIMATION_BOX_PADDING_X}", self.PAPER_BORDER_COLOR)
            
            border_consumed_len = min(self.name_len, i + self.name_len // 4)
            border_solid_part_len = self.name_len - border_consumed_len

            if border_solid_part_len > 0:
                self._safe_addstr(self.start_y + 2, name_draw_start_x,
                                  BOX_HLINE * border_solid_part_len, self.PAPER_BORDER_COLOR)
            
            flame_start_x_on_bottom_border = name_draw_start_x + border_solid_part_len
            for k_flame in range(border_consumed_len):
                self._safe_addstr(self.start_y + 2, flame_start_x_on_bottom_border + k_flame,
                                  self._get_flame_char(), self._get_flame_color_attr())
            
            right_padding_start_x = name_draw_start_x + self.name_len
            self._safe_addstr(self.start_y + 2, right_padding_start_x,
                              f"{BOX_HLINE * ANIMATION_BOX_PADDING_X}{BOX_BR}", self.PAPER_BORDER_COLOR)
            # --- END OF SEGMENTED BOTTOM BORDER HANDLING ---

            flames_below_count = min(self.name_len // 2 + 2, i + 1)
            base_flame_line_start_x = name_draw_start_x
            flame_line_offset = (self.name_len - flames_below_count) // 2
            flames_below_start_x = base_flame_line_start_x + flame_line_offset
            for k_flame in range(flames_below_count):
                self._safe_addstr(self.start_y + 3, flames_below_start_x + k_flame,
                                  self._get_flame_char(), self._get_flame_color_attr())
            
            self.stdscr.refresh()
            sleep_duration = 0.18
            if 0 < i < self.name_len and i % (max(1, self.name_len // 5 if self.name_len > 5 else 1)) == 0:
                sleep_duration = 0.30
            time.sleep(sleep_duration)

    def _animate_full_burn(self):
        for i in range(6): 
            self._clear_animation_area()

            offset1 = i % 2 
            offset2 = (i + 1) % 2 
            offset3 = i % 3

            for k in range(self.animation_width - offset1):
                self._safe_addstr(self.start_y + 0, self.start_x + k + offset1 // 2, 
                                  self._get_flame_char(), self._get_flame_color_attr())
            for k in range(self.animation_width - offset2):
                self._safe_addstr(self.start_y + 1, self.start_x + k + offset2 // 2,
                                  self._get_flame_char(), self._get_flame_color_attr())
            for k in range(self.animation_width - offset1): 
                self._safe_addstr(self.start_y + 2, self.start_x + k + offset1 // 2,
                                  self._get_flame_char(), self._get_flame_color_attr())

            flames_l3_width = max(1, self.animation_width // 2 + 1 - offset3)
            flames_l3_start_offset = (self.animation_width - flames_l3_width) // 2
            for k_l3 in range(flames_l3_width):
                self._safe_addstr(self.start_y + 3, self.start_x + flames_l3_start_offset + k_l3,
                                  self._get_flame_char(), self._get_flame_color_attr())
            
            self.stdscr.refresh()
            time.sleep(0.18)

    def _animate_embers(self):
        ember_area_start_x = self.start_x + ANIMATION_BOX_BORDER_THICKNESS
        ember_area_width = self.animation_width - (ANIMATION_BOX_BORDER_THICKNESS * 2)

        for i in range(4): 
            self._clear_animation_area()
            for anim_line_y in [self.start_y + 1, self.start_y + 2]:
                for k in range(ember_area_width):
                    is_red_ember = (k % (4 - i + 1) <= 1) or ((i < 2) and (k % 2 == 0))
                    ember_color = self.EMBER_RED if is_red_ember else self.EMBER_DARK_GREY
                    self._safe_addstr(anim_line_y, ember_area_start_x + k, self._get_ember_char(), ember_color)
            
            center_x_animation = self.start_x + self.animation_width // 2
            self._safe_addstr(self.start_y + 0, center_x_animation, self._get_ember_char(), self.EMBER_DARK_GREY)
            self._safe_addstr(self.start_y + 3, center_x_animation - 1, self._get_ember_char(), self.EMBER_DARK_GREY)
            self._safe_addstr(self.start_y + 3, center_x_animation + 1, self._get_ember_char(), self.EMBER_DARK_GREY)
            
            self.stdscr.refresh()
            time.sleep(0.35 if i > 1 else 0.25)

    def _animate_ashes(self):
        ash_area_start_x = self.start_x + ANIMATION_BOX_BORDER_THICKNESS
        base_ash_width = self.animation_width - (ANIMATION_BOX_BORDER_THICKNESS * 2)

        for i in range(5): 
            self._clear_animation_area()
            current_ash_width = max(0, base_ash_width - i * 2)
            if current_ash_width <= 0 and i > 0: continue
            ash_draw_offset_x = (base_ash_width - current_ash_width) // 2
            
            actual_width_to_draw = base_ash_width if i == 0 else current_ash_width
            actual_start_x = ash_area_start_x if i == 0 else ash_area_start_x + ash_draw_offset_x
            
            if actual_width_to_draw > 0 or i == 0:
                 for anim_line_y in [self.start_y + 1, self.start_y + 2]:
                    for k in range(actual_width_to_draw):
                        self._safe_addstr(anim_line_y, actual_start_x + k, self._get_ash_char(), self.ASH_DARK_GREY)
            
            ash_scatter_base_width = self.name_len // 2 + 1
            current_scatter_width = max(0, ash_scatter_base_width - i)
            if current_scatter_width > 0:
                scatter_offset_x = (ash_scatter_base_width - current_scatter_width) // 2
                scatter_start_x = self.start_x + (self.animation_width // 2) - (ash_scatter_base_width // 2) + scatter_offset_x
                for k in range(current_scatter_width):
                    self._safe_addstr(self.start_y + 3, scatter_start_x + k, self._get_ash_char(), self.ASH_LIGHT_GREY)

                if i < 4:
                    center_dot_x = self.start_x + self.animation_width // 2
                    self._safe_addstr(self.start_y + 3, center_dot_x, '.', self.ASH_DARK_GREY)
            
            self.stdscr.refresh()
            time.sleep(0.35)

    def _display_final_message(self):
        self._clear_animation_area() 
        self.stdscr.refresh()
        time.sleep(0.30)
        self.stdscr.clear() 

        final_message1 = f"🔥 '{self.raw_filename_str_arg}' has been turned to digital ash. 🔥"
        final_message2 = "May your worries dissipate with it."
        
        msg1_y = self.term_height // 2 - 1
        msg2_y = self.term_height // 2
        msg1_x = max(0, (self.term_width - len(final_message1)) // 2)
        msg2_x = max(0, (self.term_width - len(final_message2)) // 2)
        
        msg_color = self.FINAL_MSG_FLAME_COLOR if self.FINAL_MSG_FLAME_COLOR else self.DEFAULT_PAIR
        text_color = self.PAPER_TEXT_COLOR if self.PAPER_TEXT_COLOR else self.DEFAULT_PAIR

        self._safe_addstr(msg1_y, msg1_x, final_message1, msg_color | curses.A_BOLD)
        self._safe_addstr(msg2_y, msg2_x, final_message2, text_color)
        
        self.stdscr.refresh()
        self.stdscr.nodelay(False) 
        self.stdscr.getch() 

    def run_animation(self):
        curses.curs_set(0) 
        self.stdscr.nodelay(False) 
        
        self._init_colors() 

        if not self._setup_dimensions():
            return 

        self.stdscr.clear() 
        self.stdscr.refresh()

        self._draw_initial_paper()
        self._animate_ignition()
        self._animate_consumption()
        self._animate_full_burn()
        self._animate_embers()
        self._animate_ashes()
        self._display_final_message()


def main_cli():
    parser = argparse.ArgumentParser(
        description="bfl (Binary Flame Launcher) 🔥: Let go of digital files by simulating burning them.",
        epilog="Inspired by the therapeutic practice of burning worries written on paper."
    )
    parser.add_argument("file_to_burn", help="The path to the file you want to digitally incinerate.")
    args = parser.parse_args()

    file_to_burn_path = args.file_to_burn
    file_to_burn_basename = os.path.basename(file_to_burn_path)

    if not os.path.exists(file_to_burn_path):
        print(f"{ConfirmAnsiColors.RED}Error: File '{file_to_burn_path}' not found.{ConfirmAnsiColors.RESET}")
        sys.exit(1)
    if not os.path.isfile(file_to_burn_path):
        print(f"{ConfirmAnsiColors.RED}Error: '{file_to_burn_path}' is not a file.{ConfirmAnsiColors.RESET}")
        sys.exit(1)

    print(f"You are about to digitally incinerate: {ConfirmAnsiColors.BOLD}{file_to_burn_basename}{ConfirmAnsiColors.RESET}")
    try:
        confirm = input(f"Are you sure you want to proceed? ({ConfirmAnsiColors.GREEN}yes{ConfirmAnsiColors.RESET}/{ConfirmAnsiColors.RED}no{ConfirmAnsiColors.RESET}): ").lower()
    except EOFError: 
        print("\nIncineration cancelled due to no input.")
        sys.exit(0)

    if confirm not in ['yes', 'y']:
        print("Incineration cancelled.")
        sys.exit(0)

    file_deleted_successfully = False
    animation_completed_without_curses_error = False

    def curses_main_loop(stdscr, filename):
        animator = CursesAnimator(stdscr, filename)
        animator.run_animation()

    try:
        curses.wrapper(curses_main_loop, file_to_burn_basename)
        animation_completed_without_curses_error = True

        try:
            os.remove(file_to_burn_path)
            file_deleted_successfully = True
        except OSError as e:
            print(f"\n{ConfirmAnsiColors.RED}Animation complete, but failed to delete file '{file_to_burn_basename}': {e}{ConfirmAnsiColors.RESET}")

    except curses.error as e:
        print(f"\n{ConfirmAnsiColors.RED}A curses error occurred during animation: {e}{ConfirmAnsiColors.RESET}")
        print("The terminal might be in an unusual state. Try running 'reset'.")
    except Exception as e:
        print(f"\n{ConfirmAnsiColors.RED}An unexpected error occurred: {e}{ConfirmAnsiColors.RESET}")
    finally:
        sys.stdout.write("\033[?25h") 
        sys.stdout.flush()

        if animation_completed_without_curses_error:
            if file_deleted_successfully:
                print(f"\n{ConfirmAnsiColors.GREEN}'{file_to_burn_basename}' has been permanently deleted.{ConfirmAnsiColors.RESET}")
            elif os.path.exists(file_to_burn_path):
                print(f"\n{ConfirmAnsiColors.ORANGE}File '{file_to_burn_basename}' was NOT deleted (delete operation failed or was skipped after animation).{ConfirmAnsiColors.RESET}")
        else:
            print(f"\n{ConfirmAnsiColors.ORANGE}Animation did not complete successfully. File '{file_to_burn_basename}' was NOT deleted.{ConfirmAnsiColors.RESET}")

if __name__ == "__main__":
    main_cli()
