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

def create_widgets():
    global root, text_area, image_label, content_frame
    
    root = ctk.CTk()
    root.title("Notion-like Note Creator")
    root.geometry("800x600")
    root.minsize(600, 400)

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
    content_frame = ctk.CTkFrame(root)
    content_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Image display area
    image_label = ctk.CTkLabel(content_frame, text="")
    image_label.pack(fill="x", pady=5)

    # Text area
    text_area = ctk.CTkTextbox(content_frame)
    text_area.pack(fill="both", expand=True)

    # Right-click context menu
    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="Bold", command=toggle_bold)
    context_menu.add_command(label="Underline", command=toggle_underline)
    context_menu.add_command(label="Change Color", command=choose_color)
    context_menu.add_command(label="Change Font", command=show_font_menu)

    text_area.bind("<Button-3>", lambda event: context_menu.tk_popup(event.x_root, event.y_root))
    # Bind Ctrl+V to paste screenshot
    root.bind("<Control-v>", lambda event: paste_screenshot())

def new_note():
    global current_note_id
    current_note_id = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    text_area.delete("1.0", tk.END)
    image_label.configure(image=None)
    notes[current_note_id] = {"text": "", "image_path": None, "parent": None, "sub_notes": []}
    update_content_area()

def new_sub_note():
    global current_note_id
    if current_note_id:
        sub_note_id = f"subnote_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        notes[sub_note_id] = {"text": "", "image_path": None, "parent": current_note_id, "sub_notes": []}
        notes[current_note_id]["sub_notes"].append(sub_note_id)
        current_note_id = sub_note_id
        text_area.delete("1.0", tk.END)
        image_label.configure(image=None)
        update_content_area()
    else:
        messagebox.showwarning("Warning", "Create a parent note first!")

def save_note():
    global current_note_id
    if current_note_id:
        text = text_area.get("1.0", tk.END)
        notes[current_note_id]["text"] = text
        
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
    notes_listbox.geometry("200x400")
    
    listbox = tk.Listbox(notes_listbox, bg="#2b2b2b", fg="#ffffff")  # Dark theme for listbox
    listbox.pack(fill="both", expand=True, padx=5, pady=5)
    
    for note_id in notes:
        if not notes[note_id]["parent"]:
            listbox.insert(tk.END, note_id)
    
    listbox.bind('<<ListboxSelect>>', load_selected_note)

def load_selected_note(event):
    global current_note_id
    widget = event.widget
    selection = widget.curselection()
    if selection:
        current_note_id = widget.get(selection[0])
        note = notes[current_note_id]
        
        text_area.delete("1.0", tk.END)
        text_area.insert("1.0", note["text"])
        
        if note["image_path"]:
            img = Image.open(note["image_path"])
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            image_label.configure(image=ctk_img)
        else:
            image_label.configure(image=None)
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
            image_label.configure(image=ctk_img)
            
            notes[current_note_id]["image_path"] = save_path
        else:
            messagebox.showerror("Error", "No image found in clipboard!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to paste screenshot: {str(e)}")

def update_content_area():
    for widget in content_frame.winfo_children():
        if widget != image_label and widget != text_area:
            widget.destroy()
    
    if current_note_id and notes[current_note_id]["parent"]:
        breadcrumb_frame = ctk.CTkFrame(content_frame)
        breadcrumb_frame.pack(fill="x", pady=5)
        
        path = []
        current = current_note_id
        while current:
            path.insert(0, current)
            current = notes[current]["parent"]
        
        for i, note_id in enumerate(path):
            btn = ctk.CTkButton(breadcrumb_frame, text=note_id[:10] + "...", 
                              command=lambda nid=note_id: switch_to_note(nid))
            btn.pack(side="left", padx=2)

def switch_to_note(note_id):
    global current_note_id
    current_note_id = note_id
    note = notes[current_note_id]
    
    text_area.delete("1.0", tk.END)
    text_area.insert("1.0", note["text"])
    
    if note["image_path"]:
        img = Image.open(note["image_path"])
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        image_label.configure(image=ctk_img)
    else:
        image_label.configure(image=None)
    update_content_area()

def toggle_bold():
    current_font = text_area.cget("font")
    if isinstance(current_font, tuple) and len(current_font) >= 2:
        family = current_font[0]
        size = current_font[1]
        weight = current_font[2] if len(current_font) > 2 else "normal"
    else:
        family, size, weight = "Arial", 12, "normal"
    
    new_weight = "bold" if weight != "bold" else "normal"
    text_area.configure(font=(family, int(size), new_weight))

def toggle_underline():
    messagebox.showinfo("Info", "Underline not supported in current version")

def choose_color():
    color = colorchooser.askcolor(title="Choose Color")[1]
    if color:
        text_area.configure(text_color=color)

def show_font_menu():
    font_menu = ctk.CTkToplevel(root)
    font_menu.title("Select Font")
    font_menu.geometry("200x150")
    
    for font in ["Arial", "Times New Roman", "Calibri"]:
        ctk.CTkButton(font_menu, text=font, 
                     command=lambda f=font: [change_font(f), font_menu.destroy()]).pack(pady=5)

def change_font(font):
    current_font = text_area.cget("font")
    if isinstance(current_font, tuple) and len(current_font) >= 2:
        size = current_font[1]
        weight = current_font[2] if len(current_font) > 2 else "normal"
    else:
        size, weight = 12, "normal"
    text_area.configure(font=(font, int(size), weight))

def main():
    ctk.set_appearance_mode("dark")  # Set to dark mode
    ctk.set_default_color_theme("dark-blue")  # Use a dark theme
    
    create_widgets()
    load_notes()
    root.mainloop()

if __name__ == "__main__":
    main()