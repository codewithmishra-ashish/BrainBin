import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image, ImageGrab
import os
from datetime import datetime
import json
from reportlab.pdfgen import canvas

# Global variables
notes = {}
current_note_id = None
root = None
content_frame = None
block_widgets = []
title_label = None

def create_widgets():
    global root, content_frame, title_label
    
    root = ctk.CTk()
    root.title("Notion-like Note Editor")
    root.geometry("1000x800")
    root.minsize(800, 600)

    # Menu bar (fully functional)
    menubar = tk.Menu(root, bg="#ffffff", fg="#000000")
    root.config(menu=menubar)

    # File menu
    file_menu = tk.Menu(menubar, tearoff=0, bg="#ffffff", fg="#000000")
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="New Note", command=new_note)
    file_menu.add_command(label="New Sub-Note", command=new_sub_note)
    file_menu.add_command(label="Save", command=save_note)
    file_menu.add_command(label="Export to PDF", command=export_to_pdf)
    file_menu.add_separator()
    file_menu.add_cascade(label="Open", menu=create_open_submenu(file_menu))

    # Edit menu
    edit_menu = tk.Menu(menubar, tearoff=0, bg="#ffffff", fg="#000000")
    menubar.add_cascade(label="Edit", menu=edit_menu)
    edit_menu.add_command(label="Undo", command=lambda: root.event_generate("<<Undo>>"))
    edit_menu.add_command(label="Redo", command=lambda: root.event_generate("<<Redo>>"))
    edit_menu.add_separator()
    edit_menu.add_command(label="Cut", command=lambda: root.event_generate("<<Cut>>"))
    edit_menu.add_command(label="Copy", command=lambda: root.event_generate("<<Copy>>"))
    edit_menu.add_command(label="Paste", command=lambda: root.event_generate("<<Paste>>"))

    # Format menu
    format_menu = tk.Menu(menubar, tearoff=0, bg="#ffffff", fg="#000000")
    menubar.add_cascade(label="Format", menu=format_menu)
    format_menu.add_command(label="Bold", command=lambda: toggle_bold(get_active_text_widget()))
    format_menu.add_command(label="Italic", command=lambda: toggle_italic(get_active_text_widget()))
    format_menu.add_command(label="Underline", command=lambda: toggle_underline(get_active_text_widget()))
    format_menu.add_command(label="Font", command=lambda: show_font_menu(get_active_text_widget()))
    format_menu.add_command(label="Color", command=lambda: choose_color(get_active_text_widget()))

    # View menu
    view_menu = tk.Menu(menubar, tearoff=0, bg="#ffffff", fg="#000000")
    menubar.add_cascade(label="View", menu=view_menu)
    view_menu.add_command(label="Toggle Fullscreen", command=toggle_fullscreen)

    # Help menu
    help_menu = tk.Menu(menubar, tearoff=0, bg="#ffffff", fg="#000000")
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="About", command=show_about)

    # Content area (full screen, white background)
    content_frame = ctk.CTkFrame(root, fg_color="#ffffff")
    content_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Title (editable by double-click)
    title_frame = ctk.CTkFrame(content_frame, fg_color="#ffffff")
    title_frame.pack(fill="x", pady=10)
    title_label = ctk.CTkLabel(title_frame, text="Untitled", font=("Arial", 24, "bold"), text_color="#000000", cursor="hand2")
    title_label.pack(pady=5)
    title_label.bind("<Double-1>", lambda e: edit_title())

    # Initial block
    add_text_block()

    # Bindings
    root.bind("<Control-v>", lambda event: paste_screenshot())
    root.bind("<slash>", lambda event: show_slash_menu())
    root.bind("<Control-b>", lambda event: toggle_bold(get_active_text_widget()))
    root.bind("<Control-i>", lambda event: toggle_italic(get_active_text_widget()))
    root.bind("<Control-u>", lambda event: toggle_underline(get_active_text_widget()))
    root.bind("<Control-plus>", lambda event: increase_font_size(get_active_text_widget()))
    root.bind("<Control-minus>", lambda event: decrease_font_size(get_active_text_widget()))

def create_open_submenu(parent_menu):
    submenu = tk.Menu(parent_menu, tearoff=0, bg="#ffffff", fg="#000000")
    for note_id in notes:
        if not notes[note_id]["parent"]:
            title = notes[note_id].get("title", note_id[:15] + "...")
            submenu.add_command(label=title, command=lambda nid=note_id: switch_to_note(nid))
    return submenu

def new_note():
    global current_note_id, block_widgets, title_label
    current_note_id = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    notes[current_note_id] = {"blocks": [], "title": "Untitled", "parent": None, "sub_notes": []}
    clear_blocks()
    add_text_block()
    title_label.configure(text="Untitled")
    update_content_area()

def new_sub_note():
    global current_note_id, block_widgets, title_label
    if current_note_id:
        sub_note_id = f"subnote_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        notes[sub_note_id] = {"blocks": [], "title": "Untitled", "parent": current_note_id, "sub_notes": []}
        notes[current_note_id]["sub_notes"].append(sub_note_id)
        current_note_id = sub_note_id
        clear_blocks()
        add_text_block()
        title_label.configure(text="Untitled")
        update_content_area()
    else:
        messagebox.showwarning("Warning", "Create a parent note first!")

def save_note():
    global current_note_id, title_label
    if current_note_id:
        notes[current_note_id]["blocks"] = []
        notes[current_note_id]["title"] = title_label.cget("text")
        for widget in block_widgets:
            if isinstance(widget, tk.Text):
                text = widget.get("1.0", tk.END).strip()
                notes[current_note_id]["blocks"].append({"type": "text", "content": text})
            elif isinstance(widget, ctk.CTkFrame):
                img_path = widget.image_path
                notes[current_note_id]["blocks"].append({"type": "image", "path": img_path})
        
        with open("notes.json", "w") as f:
            json.dump(notes, f)
        messagebox.showinfo("Success", "Note saved successfully!")

def export_to_pdf():
    if not current_note_id:
        messagebox.showwarning("Warning", "No note selected!")
        return
    
    title = notes[current_note_id]["title"]
    file_path = f"{title}.pdf" if title != "Untitled" else "Untitled.pdf"
    pdf = canvas.Canvas(file_path)
    y = 750
    pdf.drawString(50, y, title)
    y -= 30
    for block in notes[current_note_id]["blocks"]:
        if block["type"] == "text":
            lines = block["content"].split("\n")
            for line in lines:
                if y < 50:
                    pdf.showPage()
                    y = 750
                pdf.drawString(50, y, line[:100])
                y -= 20
        elif block["type"] == "image" and block.get("path"):
            if y < 150:
                pdf.showPage()
                y = 750
            pdf.drawImage(block["path"], 50, y - 100, width=200, preserveAspectRatio=True)
            y -= 120
    pdf.save()
    messagebox.showinfo("Success", f"Exported to {file_path}")

def load_notes():
    try:
        with open("notes.json", "r") as f:
            global notes
            notes = json.load(f)
    except FileNotFoundError:
        pass

def switch_to_note(note_id):
    global current_note_id, block_widgets, title_label
    current_note_id = note_id
    clear_blocks()
    for block in notes[current_note_id]["blocks"]:
        if block["type"] == "text":
            text_widget = add_text_block()
            text_widget.insert("1.0", block["content"])
        elif block["type"] == "image" and block.get("path"):
            img = Image.open(block["path"])
            add_image_block(img, block["path"])
    title_label.configure(text=notes[current_note_id]["title"])
    update_content_area()

def paste_screenshot():
    global current_note_id
    try:
        img = ImageGrab.grabclipboard()
        if img:
            save_path = f"screenshots/{current_note_id}.png"
            os.makedirs("screenshots", exist_ok=True)
            img.save(save_path)
            add_image_block(img, save_path)
        else:
            messagebox.showerror("Error", "No image found in clipboard!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to paste screenshot: {str(e)}")

def add_image_block(img, path):
    global block_widgets
    frame = ctk.CTkFrame(content_frame, fg_color="#ffffff")
    frame.place(x=50, y=50)  # Initial position
    
    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
    img_label = ctk.CTkLabel(frame, image=ctk_img, text="")
    img_label.pack()
    
    frame.image_path = path
    frame.original_image = img
    
    # Drag bindings
    img_label.bind("<Button-1>", lambda e: start_drag(e, frame))
    img_label.bind("<B1-Motion>", lambda e: drag(e, frame))
    
    # Resize handles (top-left, top-right, bottom-left, bottom-right)
    for pos, (relx, rely, cursor) in [("nw", (0.0, 0.0, "size_nw_se"),), ("ne", (1.0, 0.0, "size_ne_sw"),), 
                                      ("sw", (0.0, 1.0, "size_ne_sw"),), ("se", (1.0, 1.0, "size_nw_se"),)]:
        handle = ctk.CTkLabel(frame, text="●", text_color="#666666", cursor=cursor, font=("Arial", 8))
        handle.place(relx=relx, rely=rely, anchor="center")
        handle.bind("<Button-1>", lambda e, h=handle, p=pos: start_resize(e, frame, h, p))
        handle.bind("<B1-Motion>", lambda e, h=handle, p=pos: resize_image(e, frame, h, p))
    
    block_widgets.append(frame)

def start_drag(event, widget):
    widget._drag_start_x = event.x
    widget._drag_start_y = event.y

def drag(event, widget):
    dx = event.x - widget._drag_start_x
    dy = event.y - widget._drag_start_y
    new_x = widget.winfo_x() + dx
    new_y = widget.winfo_y() + dy
    widget.place(x=new_x, y=new_y)
    reorder_blocks()

def start_resize(event, widget, handle, pos):
    widget._resize_start_x = event.x
    widget._resize_start_y = event.y
    widget._resize_start_width = widget.winfo_width()
    widget._resize_start_height = widget.winfo_height()
    widget._resize_handle_pos = pos

def resize_image(event, widget, handle, pos):
    dx = event.x - widget._resize_start_x
    dy = event.y - widget._resize_start_y
    current_width = widget._resize_start_width
    current_height = widget._resize_start_height
    
    if pos in ["nw", "se"]:
        new_width = max(current_width + dx, 50)
        new_height = max(current_height + dy, 50)
    else:  # ne, sw
        new_width = max(current_width - dx, 50)
        new_height = max(current_height + dy, 50)
    
    # Ensure proportional scaling
    aspect_ratio = widget.original_image.size[0] / widget.original_image.size[1]
    if new_width / new_height > aspect_ratio:
        new_height = new_width / aspect_ratio
    else:
        new_width = new_height * aspect_ratio
    
    ctk_img = ctk.CTkImage(light_image=widget.original_image, dark_image=widget.original_image, size=(int(new_width), int(new_height)))
    widget.winfo_children()[0].configure(image=ctk_img)
    widget.configure(width=int(new_width), height=int(new_height))

def reorder_blocks():
    global block_widgets
    block_widgets.sort(key=lambda w: w.winfo_y())

def update_content_area():
    for widget in content_frame.winfo_children():
        if widget not in block_widgets:
            widget.destroy()
    
    if current_note_id and notes[current_note_id]["parent"]:
        breadcrumb_frame = ctk.CTkFrame(content_frame, fg_color="#f0f0f0")
        breadcrumb_frame.pack(fill="x", pady=5)
        
        path = []
        current = current_note_id
        while current:
            path.insert(0, current)
            current = notes[current]["parent"]
        
        for i, note_id in enumerate(path):
            btn = ctk.CTkButton(breadcrumb_frame, text=notes[note_id]["title"] or note_id[:10] + "...", 
                              command=lambda nid=note_id: switch_to_note(nid),
                              fg_color="#e0e0e0", text_color="#000000")
            btn.pack(side="left", padx=2)

def add_text_block():
    global block_widgets
    text_widget = tk.Text(content_frame, height=2, wrap="word", bg="#ffffff", fg="#000000", font=("Arial", 16), insertbackground="#000000")
    text_widget.place(x=50, y=50)
    
    # Drag bindings
    text_widget.bind("<Button-1>", lambda e: start_drag(e, text_widget))
    text_widget.bind("<B1-Motion>", lambda e: drag(e, text_widget))
    
    # Slash command for bullets, checkboxes, and headings
    text_widget.bind("<Return>", lambda e: insert_new_block(text_widget))
    text_widget.bind("<slash>", lambda e: show_block_menu(text_widget))
    
    block_widgets.append(text_widget)
    
    # Context menu
    context_menu = tk.Menu(text_widget, tearoff=0, bg="#ffffff", fg="#000000")
    context_menu.add_command(label="Bold", command=lambda: toggle_bold(text_widget))
    context_menu.add_command(label="Italic", command=lambda: toggle_italic(text_widget))
    context_menu.add_command(label="Underline", command=lambda: toggle_underline(text_widget))
    context_menu.add_command(label="Change Color", command=lambda: choose_color(text_widget))
    context_menu.add_command(label="Change Font", command=lambda: show_font_menu(text_widget))
    text_widget.bind("<Button-3>", lambda event: context_menu.tk_popup(event.x_root, event.y_root))
    return text_widget

def edit_title():
    global title_label
    current_text = title_label.cget("text")
    title_entry = ctk.CTkEntry(title_label.master, width=200, text_color="#000000", fg_color="#ffffff")
    title_entry.insert(0, current_text)
    title_entry.pack(pady=5)
    
    def save_title(event=None):
        new_title = title_entry.get().strip() or "Untitled"
        title_label.configure(text=new_title)
        notes[current_note_id]["title"] = new_title
        title_entry.destroy()
        save_note()
    
    title_entry.bind("<Return>", save_title)
    title_entry.bind("<FocusOut>", save_title)
    title_entry.focus_set()

def insert_new_block(text_widget):
    current = text_widget.get("1.0", tk.END).strip()
    if current.endswith("/"):
        show_block_menu(text_widget)
        return "break"
    return None

def show_block_menu(text_widget):
    block_menu = ctk.CTkToplevel(root)
    block_menu.title("Block Options")
    block_menu.geometry("200x150")
    block_menu.attributes("-topmost", True)
    block_menu.configure(fg_color="#ffffff")
    
    ctk.CTkButton(block_menu, text="Bullet Point", text_color="#000000", fg_color="#f0f0f0",
                 command=lambda: [insert_bullet(text_widget), block_menu.destroy()]).pack(pady=5)
    ctk.CTkButton(block_menu, text="Checkbox", text_color="#000000", fg_color="#f0f0f0",
                 command=lambda: [insert_checkbox(text_widget), block_menu.destroy()]).pack(pady=5)
    ctk.CTkButton(block_menu, text="Heading 1", text_color="#000000", fg_color="#f0f0f0",
                 command=lambda: [insert_heading(text_widget, 1), block_menu.destroy()]).pack(pady=5)
    ctk.CTkButton(block_menu, text="Heading 2", text_color="#000000", fg_color="#f0f0f0",
                 command=lambda: [insert_heading(text_widget, 2), block_menu.destroy()]).pack(pady=5)

def insert_bullet(text_widget):
    text_widget.insert(tk.END, "\n• ")

def insert_checkbox(text_widget):
    text_widget.insert(tk.END, "\n□ ")

def insert_heading(text_widget, level):
    text_widget.insert(tk.END, f"\n{'#' * level} ")

def clear_blocks():
    global block_widgets
    for widget in block_widgets:
        widget.destroy()
    block_widgets = []

def get_active_text_widget():
    for widget in block_widgets:
        if isinstance(widget, tk.Text) and widget.focus_get() == widget:
            return widget
    return block_widgets[0] if block_widgets and isinstance(block_widgets[0], tk.Text) else None

def toggle_bold(text_widget):
    if not text_widget:
        return
    try:
        current_tags = text_widget.tag_names(tk.SEL_FIRST)
        if "bold" in current_tags:
            text_widget.tag_remove("bold", tk.SEL_FIRST, tk.SEL_LAST)
        else:
            text_widget.tag_add("bold", tk.SEL_FIRST, tk.SEL_LAST)
            current_font = text_widget.cget("font")
            text_widget.tag_configure("bold", font=(current_font[0], current_font[1], "bold"))
    except tk.TclError:
        pass

def toggle_italic(text_widget):
    if not text_widget:
        return
    try:
        current_tags = text_widget.tag_names(tk.SEL_FIRST)
        if "italic" in current_tags:
            text_widget.tag_remove("italic", tk.SEL_FIRST, tk.SEL_LAST)
        else:
            text_widget.tag_add("italic", tk.SEL_FIRST, tk.SEL_LAST)
            current_font = text_widget.cget("font")
            text_widget.tag_configure("italic", font=(current_font[0], current_font[1], "italic"))
    except tk.TclError:
        pass

def toggle_underline(text_widget):
    if not text_widget:
        return
    try:
        current_tags = text_widget.tag_names(tk.SEL_FIRST)
        if "underline" in current_tags:
            text_widget.tag_remove("underline", tk.SEL_FIRST, tk.SEL_LAST)
        else:
            text_widget.tag_add("underline", tk.SEL_FIRST, tk.SEL_LAST)
            text_widget.tag_configure("underline", underline=True)
    except tk.TclError:
        pass

def choose_color(text_widget):
    if not text_widget:
        return
    try:
        color = colorchooser.askcolor(title="Choose Color")[1]
        if color:
            text_widget.tag_add("color", tk.SEL_FIRST, tk.SEL_LAST)
            text_widget.tag_configure("color", foreground=color)
    except tk.TclError:
        pass

def show_font_menu(text_widget):
    font_menu = ctk.CTkToplevel(root)
    font_menu.title("Select Font")
    font_menu.geometry("200x150")
    font_menu.configure(fg_color="#ffffff")
    
    for font in ["Arial", "Times New Roman", "Calibri"]:
        ctk.CTkButton(font_menu, text=font, text_color="#000000", fg_color="#f0f0f0",
                     command=lambda f=font: [change_font(text_widget, f), font_menu.destroy()]).pack(pady=5)

def change_font(text_widget, font):
    if not text_widget:
        return
    try:
        current_size = text_widget.cget("font")[1] if isinstance(text_widget.cget("font"), tuple) else 16
        text_widget.tag_add("font", tk.SEL_FIRST, tk.SEL_LAST)
        text_widget.tag_configure("font", font=(font, current_size))
    except tk.TclError:
        pass

def increase_font_size(text_widget):
    if not text_widget:
        return
    try:
        current_font = text_widget.cget("font")
        current_size = current_font[1] if isinstance(current_font, tuple) else 16
        new_size = min(current_size + 2, 72)
        text_widget.configure(font=(current_font[0] if isinstance(current_font, tuple) else "Arial", new_size))
    except tk.TclError:
        pass

def decrease_font_size(text_widget):
    if not text_widget:
        return
    try:
        current_font = text_widget.cget("font")
        current_size = current_font[1] if isinstance(current_font, tuple) else 16
        new_size = max(current_size - 2, 8)
        text_widget.configure(font=(current_font[0] if isinstance(current_font, tuple) else "Arial", new_size))
    except tk.TclError:
        pass

def toggle_fullscreen():
    root.attributes("-fullscreen", not root.attributes("-fullscreen"))

def show_about():
    messagebox.showinfo("About", "Notion-like Note Editor v1.0\nA simple note-taking app inspired by Notion.")

def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    create_widgets()
    load_notes()
    root.mainloop()

if __name__ == "__main__":
    main()