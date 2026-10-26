"""
Modern Downloader
Paste a link, pick a format and quality, click Download.
Powered by yt-dlp. Needs: pip install customtkinter yt-dlp  (plus FFmpeg for MP3/MP4 merging)
"""

import os
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk # type: ignore
import yt_dlp

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MUTED = ("gray40", "gray65")  # (light mode color, dark mode color)


class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Downloader")
        self.geometry("640x600")
        self.minsize(580, 560)

        self.save_folder = str(Path.home() / "Downloads")
        self.build_ui()

    # ---------- Window layout ----------
    def build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 8))

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(
            titles, text="Downloader", font=ctk.CTkFont(size=28, weight="bold")
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles, text="Paste a link, pick a format, download.", text_color=MUTED
        ).pack(anchor="w")

        self.theme_switch = ctk.CTkSwitch(header, text="Dark", command=self.toggle_theme)
        self.theme_switch.select()
        self.theme_switch.pack(side="right")

        # Main card
        card = ctk.CTkFrame(self, corner_radius=16)
        card.pack(fill="x", padx=28, pady=12)

        # Link
        ctk.CTkLabel(card, text="Link", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=20, pady=(18, 4)
        )
        link_row = ctk.CTkFrame(card, fg_color="transparent")
        link_row.pack(fill="x", padx=20)
        self.url_entry = ctk.CTkEntry(
            link_row, placeholder_text="https://...", height=40, corner_radius=10
        )
        self.url_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            link_row, text="Paste", width=80, height=40, corner_radius=10,
            command=self.paste_link,
        ).pack(side="left", padx=(8, 0))

        # Format + quality
        ctk.CTkLabel(card, text="Format", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=20, pady=(16, 4)
        )
        format_row = ctk.CTkFrame(card, fg_color="transparent")
        format_row.pack(fill="x", padx=20)
        self.format_var = ctk.StringVar(value="MP4 Video")
        ctk.CTkSegmentedButton(
            format_row,
            values=["MP4 Video", "MP3 Audio", "Best Quality"],
            variable=self.format_var,
            command=self.on_format_change,
            height=36,
        ).pack(side="left", fill="x", expand=True)
        self.quality_menu = ctk.CTkOptionMenu(
            format_row, values=["Best", "1080p", "720p", "480p"], width=100, height=36
        )
        self.quality_menu.pack(side="left", padx=(8, 0))

        # Save folder
        ctk.CTkLabel(card, text="Save to", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=20, pady=(16, 4)
        )
        folder_row = ctk.CTkFrame(card, fg_color="transparent")
        folder_row.pack(fill="x", padx=20, pady=(0, 20))
        self.folder_label = ctk.CTkLabel(
            folder_row, text=self.short_path(), anchor="w", text_color=MUTED
        )
        self.folder_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            folder_row, text="Change", width=80, height=32, corner_radius=10,
            command=self.choose_folder,
        ).pack(side="right")

        # Download button
        self.download_btn = ctk.CTkButton(
            self, text="Download", height=48, corner_radius=12,
            font=ctk.CTkFont(size=16, weight="bold"), command=self.start_download,
        )
        self.download_btn.pack(fill="x", padx=28, pady=(8, 12))

        # Progress area
        self.progress = ctk.CTkProgressBar(self, height=10, corner_radius=5)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=28)

        self.status = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(weight="bold"))
        self.status.pack(pady=(10, 0))
        self.details = ctk.CTkLabel(self, text="", text_color=MUTED)
        self.details.pack()

        self.open_btn = ctk.CTkButton(
            self, text="Open folder", width=140, corner_radius=10,
            command=self.open_folder,
        )

    # ---------- Small UI actions ----------
    def toggle_theme(self):
        ctk.set_appearance_mode("dark" if self.theme_switch.get() else "light")
        self.theme_switch.configure(text="Dark" if self.theme_switch.get() else "Light")

    def paste_link(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, text.strip())

    def on_format_change(self, value):
        # Quality only matters for MP4 video
        self.quality_menu.configure(state="normal" if value == "MP4 Video" else "disabled")

    def short_path(self):
        path = self.save_folder
        return path if len(path) <= 50 else "..." + path[-47:]

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_folder = folder
            self.folder_label.configure(text=self.short_path())

    def open_folder(self):
        try:
            os.startfile(self.save_folder)  # Windows
        except AttributeError:
            messagebox.showinfo("Saved in", self.save_folder)

    # ---------- Download logic ----------
    def build_options(self):
        choice = self.format_var.get()
        options = {
            "outtmpl": f"{self.save_folder}/%(title)s.%(ext)s",
            "progress_hooks": [self.on_progress],
            "noplaylist": True,
            "quiet": True,
            "concurrent_fragment_downloads": 4,  # faster on sites that split files
        }

        if choice == "MP3 Audio":
            options["format"] = "bestaudio/best"
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        elif choice == "MP4 Video":
            quality = self.quality_menu.get()
            limit = "" if quality == "Best" else f"[height<={quality[:-1]}]"
            options["format"] = (
                f"bestvideo{limit}[ext=mp4]+bestaudio[ext=m4a]/"
                f"best{limit}[ext=mp4]/best{limit}/best"
            )
            options["merge_output_format"] = "mp4"
        else:
            options["format"] = "best"

        return options

    def start_download(self):
        link = self.url_entry.get().strip()
        if not link:
            messagebox.showwarning("Missing link", "Please paste a link first.")
            return

        self.download_btn.configure(state="disabled", text="Downloading...")
        self.open_btn.pack_forget()
        self.progress.set(0)
        self.status.configure(text="Starting...")
        self.details.configure(text="")

        threading.Thread(target=self.run_download, args=(link,), daemon=True).start()

    def run_download(self, link):
        try:
            with yt_dlp.YoutubeDL(self.build_options()) as ydl:
                ydl.download([link])
            self.after(0, lambda: self.finish("Done! Your file is saved."))
        except Exception as error:
            clean = re.sub(r"\x1b\[[0-9;]*m", "", str(error))
            self.after(0, lambda: self.finish(clean, failed=True))

    def on_progress(self, data):
        if data["status"] == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            if total:
                fraction = data["downloaded_bytes"] / total
            elif data.get("fragment_count"):
                fraction = data.get("fragment_index", 0) / data["fragment_count"]
            else:
                fraction = None

            speed = data.get("speed")
            eta = data.get("eta")
            parts = []
            if speed:
                parts.append(f"{speed / 1024 / 1024:.1f} MB/s")
            if eta is not None:
                parts.append(f"{eta}s left")
            detail = "   ".join(parts)

            self.after(0, lambda: self.update_progress(fraction, detail))
        elif data["status"] == "finished":
            self.after(0, lambda: self.status.configure(text="Processing file..."))

    # ---------- Updates that run on the main thread ----------
    def update_progress(self, fraction, detail):
        if fraction is not None:
            self.progress.set(min(fraction, 1))
            self.status.configure(text=f"Downloading... {fraction * 100:.0f}%")
        else:
            self.status.configure(text="Downloading...")
        self.details.configure(text=detail)

    def finish(self, message, failed=False):
        self.download_btn.configure(state="normal", text="Download")
        self.details.configure(text="")
        if failed:
            self.status.configure(text="Download failed")
            messagebox.showerror("Download failed", message)
        else:
            self.progress.set(1)
            self.status.configure(text=message)
            self.open_btn.pack(pady=12)


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
