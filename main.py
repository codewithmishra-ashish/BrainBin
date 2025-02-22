import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image, ImageGrab
import os
from datetime import datetime
import json

# Global variables
notes = {}
current_note_id = None
root = None
text_area = None
image_label = None
notes_listbox = None
content_frame = None
block_widgets = []

def create_widgets():
    global root, text_area, image_label, content_frame
    
    root = ctk.CTk()
    root.title("Notion-like Note Creator")
    root.geometry("900x700")
    root.minsize(700, 500)

    # Menu bar
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="New Note", command=new_note)
    file_menu.add_command(label="New Sub-Note", command=new_sub_note)
    file_menu.add_command(label="Save", command=save_note)
    file_menu.add_command(label="Modules", command=show_modules)

    # Content area
    content_frame = ctk.CTkFrame(root, fg_color="#ffffff")
    content_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Initial blocks
    add_text_block()

    # Bindings
    root.bind("<Control-v>", lambda event: paste_screenshot())
    root.bind("<slash>", lambda event: show_slash_menu())

def new_note():
    global current_note_id, block_widgets
    current_note_id = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    notes[current_note_id] = {"blocks": [], "parent": None, "sub_notes": []}
    clear_blocks()
    add_text_block()
    update_content_area()

def new_sub_note():
    global current_note_id, block_widgets
    if current_note_id:
        sub_note_id = f"subnote_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        notes[sub_note_id] = {"blocks": [], "parent": current_note_id, "sub_notes": []}
        notes[current_note_id]["sub_notes"].append(sub_note_id)
        current_note_id = sub_note_id
        clear_blocks()
        add_text_block()
        update_content_area()
    else:
        messagebox.showwarning("Warning", "Create a parent note first!")

def save_note():
    global current_note_id
    if current_note_id:
        notes[current_note_id]["blocks"] = []
        for widget in block_widgets:
            if isinstance(widget, tk.Text):
                text = widget.get("1.0", tk.END).strip()
                notes[current_note_id]["blocks"].append({"type": "text", "content": text})
            elif isinstance(widget, ctk.CTkLabel) and widget.cget("image"):
                notes[current_note_id]["blocks"].append({"type": "image", "path": notes[current_note_id].get("image_path")})
        
        with open("notes.json", "w") as f:
            json.dump(notes, f)
        messagebox.showinfo("Success", "Note saved successfully!")

def load_notes():
    try:
        with open("notes.json", "r") as f:
            global notes
            notes = json.load(f)
    except FileNotFoundError:
        pass

def show_modules():
    global notes_listbox
    if notes_listbox and notes_listbox.winfo_exists():
        notes_listbox.destroy()
    
    notes_listbox = ctk.CTkToplevel(root)
    notes_listbox.title("Modules")
    notes_listbox.geometry("300x500")
    
    # Tabbed view for list and table
    tabview = ctk.CTkTabview(notes_listbox)
    tabview.pack(fill="both", expand=True, padx=5, pady=5)
    
    list_tab = tabview.add("List")
    table_tab = tabview.add("Table")
    
    # List view
    listbox = tk.Listbox(list_tab, bg="#f0f0f0", fg="#000000")
    listbox.pack(fill="both", expand=True, padx=5, pady=5)
    for note_id in notes:
        if not notes[note_id]["parent"]:
            listbox.insert(tk.END, note_id)
    listbox.bind('<<ListboxSelect>>', load_selected_note)

    # Table view (simple)
    table_frame = ctk.CTkFrame(table_tab)
    table_frame.pack(fill="both", expand=True, padx=5, pady=5)
    for i, note_id in enumerate([nid for nid in notes if not notes[nid]["parent"]]):
        btn = ctk.CTkButton(table_frame, text=note_id[:15] + "...", command=lambda nid=note_id: switch_to_note(nid))
        btn.grid(row=i, column=0, pady=2, sticky="ew")
        count_label = ctk.CTkLabel(table_frame, text=f"{len(notes[note_id]['sub_notes'])} sub-notes")
        count_label.grid(row=i, column=1, padx=5)

def load_selected_note(event):
    global current_note_id, block_widgets
    widget = event.widget
    selection = widget.curselection()
    if selection:
        current_note_id = widget.get(selection[0])
        clear_blocks()
        for block in notes[current_note_id]["blocks"]:
            if block["type"] == "text":
                text_widget = add_text_block()
                text_widget.insert("1.0", block["content"])
            elif block["type"] == "image" and block.get("path"):
                img = Image.open(block["path"])
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                image_widget = ctk.CTkLabel(content_frame, image=ctk_img, text="")
                image_widget.pack(fill="x", pady=2)
                block_widgets.append(image_widget)
        update_content_area()

def paste_screenshot():
    global current_note_id
    try:
        img = ImageGrab.grabclipboard()
        if img:
            save_path = f"screenshots/{current_note_id}.png"
            os.makedirs("screenshots", exist_ok=True)
            img.save(save_path)
            
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            image_widget = ctk.CTkLabel(content_frame, image=ctk_img, text="")
            image_widget.pack(fill="x", pady=2)
            block_widgets.append(image_widget)
            
            notes[current_note_id]["image_path"] = save_path
        else:
            messagebox.showerror("Error", "No image found in clipboard!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to paste screenshot: {str(e)}")

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
            btn = ctk.CTkButton(breadcrumb_frame, text=note_id[:10] + "...", 
                              command=lambda nid=note_id: switch_to_note(nid),
                              fg_color="#e0e0e0", text_color="#000000")
            btn.pack(side="left", padx=2)

def switch_to_note(note_id):
    global current_note_id, block_widgets
    current_note_id = note_id
    clear_blocks()
    for block in notes[current_note_id]["blocks"]:
        if block["type"] == "text":
            text_widget = add_text_block()
            text_widget.insert("1.0", block["content"])
        elif block["type"] == "image" and block.get("path"):
            img = Image.open(block["path"])
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            image_widget = ctk.CTkLabel(content_frame, image=ctk_img, text="")
            image_widget.pack(fill="x", pady=2)
            block_widgets.append(image_widget)
    update_content_area()

def add_text_block():
    global block_widgets
    text_widget = tk.Text(content_frame, height=2, wrap="word", bg="#ffffff", fg="#000000", font=("Arial", 12))
    text_widget.pack(fill="x", pady=2)
    block_widgets.append(text_widget)
    
    # Context menu for formatting
    context_menu = tk.Menu(text_widget, tearoff=0)
    context_menu.add_command(label="Bold", command=lambda: toggle_bold(text_widget))
    context_menu.add_command(label="Italic", command=lambda: toggle_italic(text_widget))
    context_menu.add_command(label="Underline", command=lambda: toggle_underline(text_widget))
    context_menu.add_command(label="Change Color", command=lambda: choose_color(text_widget))
    context_menu.add_command(label="Change Font", command=lambda: show_font_menu(text_widget))
    text_widget.bind("<Button-3>", lambda event: context_menu.tk_popup(event.x_root, event.y_root))
    return text_widget

def clear_blocks():
    global block_widgets
    for widget in block_widgets:
        widget.destroy()
    block_widgets = []

def toggle_bold(text_widget):
    try:
        current_tags = text_widget.tag_names(tk.SEL_FIRST)
        if "bold" in current_tags:
            text_widget.tag_remove("bold", tk.SEL_FIRST, tk.SEL_LAST)
        else:
            text_widget.tag_add("bold", tk.SEL_FIRST, tk.SEL_LAST)
            text_widget.tag_configure("bold", font=("", 12, "bold"))
    except tk.TclError:
        pass

def toggle_italic(text_widget):
    try:
        current_tags = text_widget.tag_names(tk.SEL_FIRST)
        if "italic" in current_tags:
            text_widget.tag_remove("italic", tk.SEL_FIRST, tk.SEL_LAST)
        else:
            text_widget.tag_add("italic", tk.SEL_FIRST, tk.SEL_LAST)
            text_widget.tag_configure("italic", font=("", 12, "italic"))
    except tk.TclError:
        pass

def toggle_underline(text_widget):
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
    
    for font in ["Arial", "Times New Roman", "Calibri"]:
        ctk.CTkButton(font_menu, text=font, 
                     command=lambda f=font: [change_font(text_widget, f), font_menu.destroy()]).pack(pady=5)

def change_font(text_widget, font):
    try:
        text_widget.tag_add("font", tk.SEL_FIRST, tk.SEL_LAST)
        text_widget.tag_configure("font", font=(font, 12))
    except tk.TclError:
        pass

def show_slash_menu():
    slash_menu = ctk.CTkToplevel(root)
    slash_menu.title("Commands")
    slash_menu.geometry("200x150")
    slash_menu.attributes("-topmost", True)
    
    ctk.CTkButton(slash_menu, text="Add Text Block", command=lambda: [add_text_block(), slash_menu.destroy()]).pack(pady=5)
    ctk.CTkButton(slash_menu, text="Paste Image", command=lambda: [paste_screenshot(), slash_menu.destroy()]).pack(pady=5)

def main():
    ctk.set_appearance_mode("light")  # Light mode
    ctk.set_default_color_theme("blue")  # Light blue accents
    
    create_widgets()
    load_notes()
    root.mainloop()

if __name__ == "__main__":
    main()