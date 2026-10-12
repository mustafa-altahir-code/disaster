"""الواجهة الرئيسية لنظام إنشاء التقرير المساحي — واجهة مبسطة بتصميم هادئ وتبويبات منظمة."""

import os
import sys
import re
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

from clipboard_reader import read_clipboard
from parser import (
    parse_clipboard,
    validate,
    build_ordered_data,
    get_default_fields,
    merge_data,
)
from pdf_generator import generate_pdf

from config import (
    REQUIRED_FIELDS,
    FIELD_ORDER,
    DEFAULT_MAIN_TITLE,
    DEFAULT_COMPANY_TITLE,
    COLOR_PRIMARY,
    COLOR_PRIMARY_DARK,
    COLOR_SECONDARY,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_BTN_PRINT,
    COLOR_BTN_PRINT_HOVER,
    COLOR_DELETE,
    COLOR_DELETE_ACTIVE,
    APP_ICON,
)


class RoundedButton(tk.Canvas):
    """زر بتصميم أنيق بحواف مستديرة ناعمة وتأثيرات تفاعلية."""

    def __init__(
        self,
        parent,
        text,
        command=None,
        bg="#143D66",
        hover_bg="#0F2E4D",
        fg="white",
        radius=8,
        height=32,
        font=("Segoe UI", 9, "bold"),
        **kwargs,
    ):
        parent_bg = parent.cget("bg") if hasattr(parent, "cget") else "#FFFFFF"
        super().__init__(
            parent,
            height=height,
            bg=parent_bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            **kwargs,
        )
        self.command = command
        self.text = text
        self.normal_bg = bg
        self.hover_bg = hover_bg
        self.pressed_bg = hover_bg
        self.current_bg = bg
        self.fg_color = fg
        self.radius = radius
        self.font = font
        self.btn_height = height
        self._disabled = False

        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.btn_height
        if w < 10 or h < 10:
            return

        r = min(self.radius, h // 2, w // 2)
        color = "#94A3B8" if self._disabled else self.current_bg

        self.create_arc((0, 0, 2 * r, 2 * r), start=90, extent=90, fill=color, outline=color)
        self.create_arc((w - 2 * r, 0, w, 2 * r), start=0, extent=90, fill=color, outline=color)
        self.create_arc((0, h - 2 * r, 2 * r, h), start=180, extent=90, fill=color, outline=color)
        self.create_arc((w - 2 * r, h - 2 * r, w, h), start=270, extent=90, fill=color, outline=color)
        self.create_rectangle((r, 0, w - r, h), fill=color, outline=color)
        self.create_rectangle((0, r, w, h - r), fill=color, outline=color)

        self.create_text(
            w / 2,
            h / 2,
            text=self.text,
            fill=self.fg_color,
            font=self.font,
        )

    def _on_enter(self, e):
        if not self._disabled:
            self.current_bg = self.hover_bg
            self._draw()

    def _on_leave(self, e):
        if not self._disabled:
            self.current_bg = self.normal_bg
            self._draw()

    def _on_press(self, e):
        if not self._disabled:
            self.current_bg = self.pressed_bg
            self._draw()

    def _on_release(self, e):
        if not self._disabled:
            self.current_bg = self.hover_bg
            self._draw()
            if self.command:
                self.command()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root

        # تهيئة الحقول كاملة
        self.data = get_default_fields(FIELD_ORDER)
        self.aerial_image = None
        self.thumb_photo = None

        # عناصر التحرير داخل الجداول
        self.edit_container = None
        self.edit_entry = None
        self.edit_item = None
        self.active_tree = None

        self.output = self._get_output_folder()

        self._configure_window()
        self._build_ui()
        self.refresh_all_views()

    # ══════════════════════════════════════════════════════════
    # الإعدادات
    # ══════════════════════════════════════════════════════════

    def _get_output_folder(self):
        desktop = os.path.join(
            os.path.expanduser("~"),
            "Desktop",
        )
        folder = os.path.join(
            desktop,
            "Survey Reports",
        )
        os.makedirs(folder, exist_ok=True)
        return folder

    def _configure_window(self):
        self.root.title("Survey Report v1.1")
        self.root.geometry("1100x720")
        self.root.minsize(940, 620)
        self.root.configure(bg="#F1F5F9")

        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(self.root.attributes, "-topmost", False)
        self.root.focus_force()

        if os.path.exists(APP_ICON):
            try:
                self.root.iconbitmap(APP_ICON)
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════
    # بناء الواجهة
    # ══════════════════════════════════════════════════════════

    def _build_ui(self):
        self._build_header()
        self._build_content()
        self._build_status_bar()

    def _build_header(self):
        header = tk.Frame(
            self.root,
            bg=COLOR_PRIMARY,
            height=52,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg=COLOR_PRIMARY)
        title_box.pack(side="right", padx=18, pady=8)

        tk.Label(
            title_box,
            text="نظام إنشاء التقارير المساحية",
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
        ).pack(side="right")

        # tk.Label(
        #     title_box,
        #     text="  |  إصدار التقارير المساحية الرسمية",
        #     font=("Segoe UI", 9),
        #     bg=COLOR_PRIMARY,
        #     fg="#94A3B8",
        # ).pack(side="right")

        folder_badge = tk.Frame(header, bg="#102F4E", padx=8, pady=3)
        folder_badge.pack(side="left", padx=15, pady=11)

        tk.Label(
            folder_badge,
            text="📁 مجلد الحفظ: Survey Reports",
            font=("Segoe UI", 8),
            bg="#102F4E",
            fg="#E2E8F0",
        ).pack()

    def _build_content(self):
        container = tk.Frame(
            self.root,
            bg="#F1F5F9",
        )
        container.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=10,
        )

        # ──────────────────────────────────────────────────────
        # لوحة التحكم الجانبية (يمين) — مبسطة ومريحة وبدون زحام
        # ──────────────────────────────────────────────────────
        controls = tk.Frame(
            container,
            bg="#FFFFFF",
            width=230,
            highlightbackground="#CBD5E1",
            highlightthickness=1,
        )
        controls.pack(
            side="right",
            fill="y",
            padx=(10, 0),
        )
        controls.pack_propagate(False)

        tk.Label(
            controls,
            text="لوحة التحكم",
            font=("Segoe UI", 11, "bold"),
            bg="#FFFFFF",
            fg=COLOR_PRIMARY,
        ).pack(pady=(12, 6))

        # خيارا اللصق المنفصل فقط (حسب طلب المستخدم)
        tk.Label(
            controls,
            text="خيارات اللصق من المتصفح",
            font=("Segoe UI", 8, "bold"),
            bg="#FFFFFF",
            fg="#64748B",
        ).pack(pady=(2, 4))

        # 1. زر لصق بيانات الملاك والصك
        btn_deed = RoundedButton(
            controls,
            "📋  لصق بيانات الملاك والصك",
            command=self.on_paste_deed,
            bg="#143D66",
            hover_bg="#0F2E4D",
            radius=8,
            height=34,
            font=("Segoe UI", 9, "bold"),
        )
        btn_deed.pack(fill="x", padx=12, pady=3)

        # 2. زر لصق بيانات القطعة
        btn_prop = RoundedButton(
            controls,
            "📋  لصق بيانات القطعة",
            command=self.on_paste_property,
            bg="#1E5D8F",
            hover_bg="#17486E",
            radius=8,
            height=34,
            font=("Segoe UI", 9, "bold"),
        )
        btn_prop.pack(fill="x", padx=12, pady=3)

        self._add_separator(controls)

        # قسم الصورة الجوية
        RoundedButton(
            controls,
            "🖼  رفع الصورة الجوية",
            command=self.on_upload_image,
            bg="#475569",
            hover_bg="#334155",
            radius=8,
            height=28,
            font=("Segoe UI", 8, "bold"),
        ).pack(fill="x", padx=12, pady=2)

        self.image_preview_canvas = tk.Canvas(
            controls,
            width=200,
            height=85,
            bg="#F8FAFC",
            highlightbackground="#E2E8F0",
            highlightthickness=1,
            bd=0,
        )
        self.image_preview_canvas.pack(padx=12, pady=(4, 2))
        self._update_image_preview()

        self.image_status_var = tk.StringVar(value="لا توجد صورة جوية")
        tk.Label(
            controls,
            textvariable=self.image_status_var,
            font=("Segoe UI", 8),
            bg="#FFFFFF",
            fg="#64748B",
            wraplength=190,
            justify="center",
        ).pack(padx=10, pady=(0, 2))

        RoundedButton(
            controls,
            "🗑  حذف الصورة",
            command=self.on_remove_image,
            bg=COLOR_DELETE,
            hover_bg=COLOR_DELETE_ACTIVE,
            radius=6,
            height=24,
            font=("Segoe UI", 7, "bold"),
        ).pack(fill="x", padx=12, pady=2)

        self._add_separator(controls)

        # قسم إنشاء التقرير
        RoundedButton(
            controls,
            "🖨  إنشاء PDF",
            command=self.on_print,
            bg=COLOR_BTN_PRINT,
            hover_bg=COLOR_BTN_PRINT_HOVER,
            radius=10,
            height=36,
            font=("Segoe UI", 10, "bold"),
        ).pack(fill="x", padx=12, pady=3)

        RoundedButton(
            controls,
            "📁  فتح مجلد التقارير",
            command=self.on_open_folder,
            bg="#334155",
            hover_bg="#1E293B",
            radius=8,
            height=28,
            font=("Segoe UI", 8),
        ).pack(fill="x", padx=12, pady=2)

        RoundedButton(
            controls,
            "🧹  تفريغ البيانات",
            command=self.on_clear,
            bg="#64748B",
            hover_bg="#475569",
            radius=8,
            height=26,
            font=("Segoe UI", 8),
        ).pack(fill="x", padx=12, pady=3)

        self.file_var = tk.StringVar(value="")
        tk.Label(
            controls,
            textvariable=self.file_var,
            font=("Segoe UI", 8, "bold"),
            bg="#FFFFFF",
            fg="#15803D",
            wraplength=195,
            justify="center",
        ).pack(side="bottom", padx=10, pady=8)

        # ──────────────────────────────────────────────────────
        # المنطقة الرئيسية مع التبويبات (يسار)
        # ──────────────────────────────────────────────────────
        main_area = tk.Frame(
            container,
            bg="#F1F5F9",
        )
        main_area.pack(
            side="left",
            fill="both",
            expand=True,
        )

        # شريط التبويبات العلوي المصمم باحترافية عصرية (Segmented Tab Bar)
        tab_header_bar = tk.Frame(
            main_area,
            bg="#F1F5F9",
            height=44,
        )
        tab_header_bar.pack(
            fill="x",
            padx=12,
            pady=(6, 4),
        )
        tab_header_bar.pack_propagate(False)

        # حاوية التبويبات الكبسولية على اليمين (متوافقة مع الاتجاه العربي)
        tabs_pill_container = tk.Frame(
            tab_header_bar,
            bg="#E2E8F0",
            highlightbackground="#CBD5E1",
            highlightthickness=1,
            padx=3,
            pady=3,
        )
        tabs_pill_container.pack(side="right")

        def on_tab_click(index):
            self.notebook.select(index)
            self._update_tab_styles(index)

        # التاب 1: بيانات التقرير
        self.btn_tab_report = RoundedButton(
            tabs_pill_container,
            text="📋  بيانات التقرير",
            command=lambda: on_tab_click(0),
            bg=COLOR_PRIMARY,
            hover_bg=COLOR_PRIMARY_DARK,
            fg="#FFFFFF",
            radius=6,
            height=28,
            font=("Segoe UI", 9, "bold"),
            width=135,
        )
        self.btn_tab_report.pack(side="right", padx=2)

        # التاب 2: الإدخال والتحرير اليدوي
        self.btn_tab_manual = RoundedButton(
            tabs_pill_container,
            text="✍️  الإدخال اليدوي",
            command=lambda: on_tab_click(1),
            bg="#E2E8F0",
            hover_bg="#CBD5E1",
            fg="#475569",
            radius=6,
            height=28,
            font=("Segoe UI", 9, "bold"),
            width=135,
        )
        self.btn_tab_manual.pack(side="right", padx=2)

        self.tab_title_var = tk.StringVar(value="المعاينة المباشرة لبيانات التقرير الحالية")
        tk.Label(
            tab_header_bar,
            textvariable=self.tab_title_var,
            font=("Segoe UI", 9),
            bg="#F1F5F9",
            fg="#64748B",
        ).pack(side="left", pady=8)

        # إخفاء تبويبات ttk الافتراضية واعتماد شريط التبويبات المخصص
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.layout("Custom.TNotebook.Tab", [])
        style.configure(
            "Custom.TNotebook",
            background="#F1F5F9",
            borderwidth=0,
            highlightthickness=0,
        )

        self.notebook = ttk.Notebook(main_area, style="Custom.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        # التاب 1: بيانات التقرير (المعاينة واللصق)
        self.tab_report = tk.Frame(self.notebook, bg="#FFFFFF")
        self.notebook.add(self.tab_report, text="📋  بيانات التقرير")

        # التاب 2: الإدخال والتحرير اليدوي
        self.tab_manual = tk.Frame(self.notebook, bg="#FFFFFF")
        self.notebook.add(self.tab_manual, text="✍️  الإدخال اليدوي")

        self._build_report_tab()
        self._build_manual_tab()

    def _update_tab_styles(self, active_index):
        """تحديث شكل التبويبات الكبسولية عند التبديل."""
        if active_index == 0:
            self.btn_tab_report.normal_bg = COLOR_PRIMARY
            self.btn_tab_report.hover_bg = COLOR_PRIMARY_DARK
            self.btn_tab_report.current_bg = COLOR_PRIMARY
            self.btn_tab_report.fg_color = "#FFFFFF"
            self.btn_tab_report._draw()

            self.btn_tab_manual.normal_bg = "#E2E8F0"
            self.btn_tab_manual.hover_bg = "#CBD5E1"
            self.btn_tab_manual.current_bg = "#E2E8F0"
            self.btn_tab_manual.fg_color = "#475569"
            self.btn_tab_manual._draw()

            self.tab_title_var.set("المعاينة المباشرة لبيانات التقرير الحالية")
        else:
            self.btn_tab_report.normal_bg = "#E2E8F0"
            self.btn_tab_report.hover_bg = "#CBD5E1"
            self.btn_tab_report.current_bg = "#E2E8F0"
            self.btn_tab_report.fg_color = "#475569"
            self.btn_tab_report._draw()

            self.btn_tab_manual.normal_bg = COLOR_PRIMARY
            self.btn_tab_manual.hover_bg = COLOR_PRIMARY_DARK
            self.btn_tab_manual.current_bg = COLOR_PRIMARY
            self.btn_tab_manual.fg_color = "#FFFFFF"
            self.btn_tab_manual._draw()

            self.tab_title_var.set("تحرير وإدخال الحقول يدويًا مع إضافة ملاك ونقاط")

    def _build_report_tab(self):
        """بناء تاب معاينة التقرير (عرض نظيف ومريح للبيانات النشطة)."""
        top_bar = tk.Frame(
            self.tab_report,
            bg="#FFFFFF",
            height=40,
        )
        top_bar.pack(fill="x", padx=12, pady=(6, 2))
        top_bar.pack_propagate(False)

        right_info = tk.Frame(top_bar, bg="#FFFFFF")
        right_info.pack(side="right", pady=4)

        tk.Label(
            right_info,
            text="بيانات التقرير الحالي",
            font=("Segoe UI", 11, "bold"),
            bg="#FFFFFF",
            fg=COLOR_PRIMARY,
        ).pack(side="right")

        self.report_counter_var = tk.StringVar(value="0 حقل مكتمل")
        tk.Label(
            right_info,
            textvariable=self.report_counter_var,
            font=("Segoe UI", 8, "bold"),
            bg="#E2E8F0",
            fg="#334155",
            padx=8,
            pady=1,
        ).pack(side="right", padx=(8, 0))

        tk.Label(
            top_bar,
            text="* انقر مرتين على أي قيمة لتعديلها مباشرة",
            font=("Segoe UI", 8),
            bg="#FFFFFF",
            fg="#64748B",
        ).pack(side="left", pady=6)

        table_frame = tk.Frame(
            self.tab_report,
            bg="#FFFFFF",
            highlightbackground="#CBD5E1",
            highlightthickness=1,
        )
        table_frame.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        self.tree_report = self._create_treeview(table_frame)
        self.tree_report.bind("<Double-1>", lambda e: self._start_inline_edit(e, self.tree_report))
        self.tree_report.bind("<Return>", lambda e: self._start_inline_edit(e, self.tree_report))

    def _build_manual_tab(self):
        """بناء تاب الإدخال اليدوي المنفصل (يحتوي على كافة الحقول جاهزة للعمل اليدوي)."""
        top_bar = tk.Frame(
            self.tab_manual,
            bg="#FFFFFF",
            height=42,
        )
        top_bar.pack(fill="x", padx=12, pady=(6, 2))
        top_bar.pack_propagate(False)

        tk.Label(
            top_bar,
            text="إدخال وتحرير الحقول يدوياً",
            font=("Segoe UI", 11, "bold"),
            bg="#FFFFFF",
            fg=COLOR_PRIMARY,
        ).pack(side="right", pady=4)

        # أزرار الإضافة اليدوية داخل التاب اليدوي حصراً
        btn_tools = tk.Frame(top_bar, bg="#FFFFFF")
        btn_tools.pack(side="left", pady=2)

        RoundedButton(
            btn_tools,
            "➕ إضافة مالك",
            command=self.on_add_owner,
            bg="#0284C7",
            hover_bg="#0369A1",
            radius=6,
            height=26,
            font=("Segoe UI", 8, "bold"),
            width=90,
        ).pack(side="left", padx=4)

        RoundedButton(
            btn_tools,
            "➕ إضافة إحداثي",
            command=self.on_add_coordinate,
            bg="#0D9488",
            hover_bg="#0F766E",
            radius=6,
            height=26,
            font=("Segoe UI", 8, "bold"),
            width=95,
        ).pack(side="left", padx=4)

        RoundedButton(
            btn_tools,
            "🗑 حذف الحقل",
            command=self.on_delete_selected_field,
            bg=COLOR_DELETE,
            hover_bg=COLOR_DELETE_ACTIVE,
            radius=6,
            height=26,
            font=("Segoe UI", 8),
            width=80,
        ).pack(side="left", padx=4)

        table_frame = tk.Frame(
            self.tab_manual,
            bg="#FFFFFF",
            highlightbackground="#CBD5E1",
            highlightthickness=1,
        )
        table_frame.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        self.tree_manual = self._create_treeview(table_frame)
        self.tree_manual.bind("<Double-1>", lambda e: self._start_inline_edit(e, self.tree_manual))
        self.tree_manual.bind("<Return>", lambda e: self._start_inline_edit(e, self.tree_manual))

    def _create_treeview(self, parent):
        """إنشاء جدول منسق ومسطر."""
        tree = ttk.Treeview(
            parent,
            columns=("field", "value"),
            show="headings",
            style="Custom.Treeview",
        )
        tree.heading("field", text="الحقل")
        tree.heading("value", text="القيمة")

        tree.column("field", width=250, anchor="e", stretch=False)
        tree.column("value", width=520, anchor="e", stretch=True)

        tree.tag_configure("even", background="#FFFFFF")
        tree.tag_configure("odd", background="#F8FAFC")

        scroll = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=tree.yview,
        )
        tree.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        return tree

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="")

        status_frame = tk.Frame(
            self.root,
            bg="#E2E8F0",
            height=26,
        )
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)

        # tk.Label(
        #     status_frame,
        #     textvariable=self.status_var,
        #     bg="#E2E8F0",
        #     fg="#334155",
        #     font=("Segoe UI", 8),
        #     anchor="e",
        #     padx=12,
        # ).pack(side="right", fill="y")

        tk.Label(
            status_frame,
            text="Survey Report v1.1",
            bg="#E2E8F0",
            fg="#64748B",
            font=("Segoe UI", 8),
            anchor="w",
            padx=12,
        ).pack(side="left", fill="y")

    # ══════════════════════════════════════════════════════════
    # المكونات المساعدة
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _add_separator(parent):
        sep = tk.Frame(parent, bg="#E2E8F0", height=1)
        sep.pack(fill="x", padx=12, pady=6)

    def set_status(self, text):
        self.status_var.set(text)

    # ══════════════════════════════════════════════════════════
    # تحديث وتعديل الجداول
    # ══════════════════════════════════════════════════════════

    def refresh_all_views(self):
        self._cancel_inline_edit()

        # 1. تحديث تاب بيانات التقرير (يعرض الحقول الممتلئة أو الأساسية)
        for item in self.tree_report.get_children():
            self.tree_report.delete(item)

        idx_report = 0
        filled_count = 0
        for key, value in self.data.items():
            val_str = str(value) if value is not None else ""
            if val_str:
                filled_count += 1
                tag = "even" if idx_report % 2 == 0 else "odd"
                self.tree_report.insert(
                    "",
                    "end",
                    values=(key, val_str),
                    tags=(tag,),
                )
                idx_report += 1

        self.report_counter_var.set(f"{filled_count} حقل مكتمل")

        # 2. تحديث تاب الإدخال اليدوي (يعرض كافة الحقول كاملة بما فيها الفارغة)
        for item in self.tree_manual.get_children():
            self.tree_manual.delete(item)

        idx_manual = 0
        for key, value in self.data.items():
            val_str = str(value) if value is not None else ""
            tag = "even" if idx_manual % 2 == 0 else "odd"
            self.tree_manual.insert(
                "",
                "end",
                values=(key, val_str),
                tags=(tag,),
            )
            idx_manual += 1

    def _start_inline_edit(self, event, tree):
        item = tree.identify_row(event.y) if event else None
        if not item:
            sel = tree.selection()
            item = sel[0] if sel else None

        if not item:
            return

        self._start_inline_edit_item(tree, item)

    def _start_inline_edit_item(self, tree, item):
        self._cancel_inline_edit()

        bbox = tree.bbox(item, "#2")
        if not bbox:
            return

        x, y, width, height = bbox
        values = tree.item(item, "values")
        current_value = values[1] if len(values) >= 2 else ""

        # إطار مسطر مع خط سفلي بلون كحلي راقٍ
        container = tk.Frame(
            tree,
            bg="#FFFFFF",
            highlightbackground="#CBD5E1",
            highlightthickness=1,
        )

        entry = tk.Entry(
            container,
            font=("Segoe UI", 9),
            justify="right",
            relief="flat",
            bd=0,
            bg="#FFFDF2",
            fg="#0F172A",
        )
        entry.insert(0, current_value)
        entry.pack(fill="both", expand=True, padx=4, pady=(2, 0))

        underline = tk.Frame(container, bg=COLOR_PRIMARY, height=2)
        underline.pack(fill="x", side="bottom")

        container.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        entry.select_range(0, "end")

        self.edit_container = container
        self.edit_entry = entry
        self.edit_item = item
        self.active_tree = tree

        entry.bind("<Return>", lambda e: self._save_inline_edit(move_next=True))
        entry.bind("<Tab>", lambda e: (self._save_inline_edit(move_next=True), "break")[1])
        entry.bind("<Shift-Tab>", lambda e: (self._save_inline_edit(move_prev=True), "break")[1])
        entry.bind("<Escape>", lambda e: self._cancel_inline_edit())
        entry.bind("<FocusOut>", lambda e: self._save_inline_edit(move_next=False))

    def _save_inline_edit(self, move_next=False, move_prev=False):
        if not self.edit_entry or not self.edit_item or not self.active_tree:
            return

        item = self.edit_item
        tree = self.active_tree
        value = self.edit_entry.get().strip()
        values = list(tree.item(item, "values"))

        if len(values) >= 2:
            key = values[0]
            self.data[key] = value

        self._cancel_inline_edit()
        self.refresh_all_views()
        self.set_status("✓ تم حفظ تعديل الحقل")

        if move_next or move_prev:
            children = tree.get_children()
            try:
                cur_idx = children.index(item)
                if move_next and cur_idx + 1 < len(children):
                    next_item = children[cur_idx + 1]
                    tree.selection_set(next_item)
                    tree.see(next_item)
                    self.root.after(15, lambda: self._start_inline_edit_item(tree, next_item))
                elif move_prev and cur_idx - 1 >= 0:
                    prev_item = children[cur_idx - 1]
                    tree.selection_set(prev_item)
                    tree.see(prev_item)
                    self.root.after(15, lambda: self._start_inline_edit_item(tree, prev_item))
            except ValueError:
                pass

    def _cancel_inline_edit(self):
        if self.edit_container:
            try:
                self.edit_container.destroy()
            except tk.TclError:
                pass

        self.edit_container = None
        self.edit_entry = None
        self.edit_item = None
        self.active_tree = None

    # ══════════════════════════════════════════════════════════
    # خيارا اللصق (الملاك والصك / بيانات القطعة)
    # ══════════════════════════════════════════════════════════

    def on_paste_deed(self):
        """لصق بيانات الملاك والصك (المرحلة الأولى من المتصفح)."""
        text = read_clipboard()
        if not text:
            messagebox.showwarning("الحافظة فارغة", "انسخ بيانات الصك والملاك من إضافة المتصفح أولاً.")
            return

        new_data = parse_clipboard(text)
        if not new_data:
            messagebox.showerror("خطأ في البيانات", "لم يتم التعرف على بيانات الصك المنسوخة.")
            return

        self.data = merge_data(self.data, new_data, FIELD_ORDER)
        self.refresh_all_views()
        self.notebook.select(self.tab_report)

        owner_count = sum(1 for k in new_data if k.startswith("اسم المالك")) or 1
        self.set_status(f"✓ تم لصق بيانات الملاك والصك بنجاح ({owner_count} مالك)")

    def on_paste_property(self):
        """لصق بيانات القطعة والعقار والإحداثيات (المرحلة الثانية من المتصفح)."""
        text = read_clipboard()
        if not text:
            messagebox.showwarning("الحافظة فارغة", "انسخ بيانات القطعة من إضافة المتصفح أولاً.")
            return

        new_data = parse_clipboard(text)
        if not new_data:
            messagebox.showerror("خطأ في البيانات", "لم يتم التعرف على بيانات القطعة المنسوخة.")
            return

        self.data = merge_data(self.data, new_data, FIELD_ORDER)
        self.refresh_all_views()
        self.notebook.select(self.tab_report)

        filled_count = sum(1 for v in new_data.values() if v)
        self.set_status(f"✓ تم لصق بيانات القطعة بنجاح ({filled_count} قيمة)")

    # ══════════════════════════════════════════════════════════
    # الإدارة اليدوية للحقول (داخل التاب اليدوي)
    # ══════════════════════════════════════════════════════════

    def on_add_owner(self):
        """إضافة مالك إضافي."""
        existing_indices = []
        for k in self.data:
            m = re.match(r"^اسم المالك (\d+)$", k)
            if m:
                existing_indices.append(int(m.group(1)))
        next_idx = max(existing_indices) + 1 if existing_indices else 2

        self.data[f"اسم المالك {next_idx}"] = ""
        self.data[f"رقم الهوية {next_idx}"] = ""
        self.data = build_ordered_data(self.data, FIELD_ORDER)
        self.refresh_all_views()

        # التمرير إلى المالك المضاف في التاب اليدوي
        self.notebook.select(self.tab_manual)
        for item in self.tree_manual.get_children():
            if self.tree_manual.item(item, "values")[0] == f"اسم المالك {next_idx}":
                self.tree_manual.selection_set(item)
                self.tree_manual.see(item)
                self.root.after(20, lambda: self._start_inline_edit_item(self.tree_manual, item))
                break

        self.set_status(f"✓ تمت إضافة المالك {next_idx} — أدخل الاسم ورقم الهوية")

    def on_add_coordinate(self):
        """إضافة نقطة إحداثي إضافية."""
        existing_indices = []
        for k in self.data:
            m = re.match(r"^الإحداثي الشمالي \(N\) (\d+)$", k)
            if m:
                existing_indices.append(int(m.group(1)))
        next_idx = max(existing_indices) + 1 if existing_indices else 5

        self.data[f"الإحداثي الشمالي (N) {next_idx}"] = ""
        self.data[f"الإحداثي الشرقي (E) {next_idx}"] = ""
        self.data = build_ordered_data(self.data, FIELD_ORDER)
        self.refresh_all_views()

        self.notebook.select(self.tab_manual)
        for item in self.tree_manual.get_children():
            if self.tree_manual.item(item, "values")[0] == f"الإحداثي الشمالي (N) {next_idx}":
                self.tree_manual.selection_set(item)
                self.tree_manual.see(item)
                self.root.after(20, lambda: self._start_inline_edit_item(self.tree_manual, item))
                break

        self.set_status(f"✓ تمت إضافة نقطة إحداثي {next_idx}")

    def on_delete_selected_field(self):
        """حذف الحقل المحدد في التاب اليدوي."""
        sel = self.tree_manual.selection()
        if not sel:
            messagebox.showinfo("تنبيه", "حدد حقلاً لحذفه من التاب اليدوي.")
            return

        item = sel[0]
        vals = self.tree_manual.item(item, "values")
        if not vals:
            return

        key = vals[0]
        if messagebox.askyesno("تأكيد الحذف", f"هل ترغب في حذف الحقل:\n{key}؟"):
            self._cancel_inline_edit()
            if key in self.data:
                del self.data[key]
            self.refresh_all_views()
            self.set_status(f"✓ تم حذف الحقل: {key}")

    def on_clear(self):
        """تفريغ كافة البيانات."""
        has_content = any(bool(v) for v in self.data.values()) or bool(self.aerial_image)
        if not has_content:
            return

        if not messagebox.askyesno(
            "تأكيد التفريغ",
            "هل أنت متأكد من تفريغ كافة البيانات الحالية؟",
        ):
            return

        self._cancel_inline_edit()
        self.data = get_default_fields(FIELD_ORDER)
        self.aerial_image = None
        self.refresh_all_views()
        self._update_image_preview()
        self.image_status_var.set("لا توجد صورة جوية")
        self.file_var.set("")
        self.set_status("✓ تم تفريغ البيانات بالكامل")

    # ══════════════════════════════════════════════════════════
    # إدارة ومعاينة الصورة الجوية
    # ══════════════════════════════════════════════════════

    def _update_image_preview(self):
        self.image_preview_canvas.delete("all")

        if not self.aerial_image or not os.path.exists(self.aerial_image):
            self.image_preview_canvas.create_text(
                100, 32,
                text="🖼",
                font=("Segoe UI", 16),
                fill="#94A3B8",
            )
            self.image_preview_canvas.create_text(
                100, 58,
                text="معاينة الصورة الجوية",
                font=("Segoe UI", 8),
                fill="#94A3B8",
            )
            self.thumb_photo = None
            return

        try:
            img = Image.open(self.aerial_image)
            img.thumbnail((195, 80), Image.Resampling.LANCZOS)
            self.thumb_photo = ImageTk.PhotoImage(img)
            self.image_preview_canvas.create_image(
                100, 42,
                image=self.thumb_photo,
                anchor="center",
            )
        except Exception:
            self.image_preview_canvas.create_text(
                100, 42,
                text="تعذر عرض المعاينة",
                font=("Segoe UI", 8),
                fill="#DC2626",
            )
            self.thumb_photo = None

    def on_upload_image(self):
        path = filedialog.askopenfilename(
            title="اختر الصورة الجوية",
            filetypes=[
                ("ملفات الصور", "*.png *.jpg *.jpeg *.bmp"),
                ("جميع الملفات", "*.*"),
            ],
        )

        if not path:
            return

        self.aerial_image = path
        filename = os.path.basename(path)
        if len(filename) > 22:
            filename = filename[:19] + "..."

        self.image_status_var.set(f"✓ {filename}")
        self._update_image_preview()
        self.set_status("✓ تم تحميل الصورة الجوية")

    def on_remove_image(self):
        if not self.aerial_image:
            return

        self.aerial_image = None
        self.image_status_var.set("لا توجد صورة جوية")
        self._update_image_preview()
        self.set_status("✓ تم حذف الصورة الجوية")

    # ══════════════════════════════════════════════════════════
    # إنشاء الـ PDF وفتح المجلد
    # ══════════════════════════════════════════════════════

    def on_print(self):
        self._cancel_inline_edit()

        filled = sum(1 for v in self.data.values() if v)
        if filled == 0:
            messagebox.showinfo(
                "تنبيه",
                "يرجى لصق أو إدخال بيانات التقرير أولاً.",
            )
            return

        valid, missing = validate(self.data, REQUIRED_FIELDS)
        if not valid:
            if not messagebox.askyesno(
                "حقول فارغة",
                "الحقول الأساسية التالية لا تزال فارغة:\n\n"
                + "\n".join(f"• {field}" for field in missing)
                + "\n\nهل ترغب في المتابعة وإنشاء التقرير على أي حال؟",
            ):
                return

        try:
            order_no = str(
                self.data.get("رقم الطلب", "")
                or self.data.get("رقم_الطلب", "")
                or self.data.get("application_number", "")
            ).strip()
            safe_order_no = re.sub(r'[\\/*?:"<>|\r\n\t]', '', order_no).strip()

            if not safe_order_no:
                from tkinter import simpledialog
                prompt_order = simpledialog.askstring(
                    "رقم الطلب مطلوب",
                    "يرجى إدخال رقم الطلب لتسمية ملف التقرير (مثال: DU221511):",
                    parent=self.root,
                )
                if prompt_order and prompt_order.strip():
                    safe_order_no = re.sub(r'[\\/*?:"<>|\r\n\t]', '', prompt_order).strip()
                    self.data["رقم الطلب"] = safe_order_no
                    self.refresh_all_views()

            if not safe_order_no:
                messagebox.showwarning(
                    "تنبيه",
                    "رقم الطلب مطلوب دائمًا لتسمية ملف التقرير.",
                )
                return

            filename = f"{safe_order_no}.pdf"

            path = generate_pdf(
                self.data,
                output_path=os.path.join(
                    self.output,
                    filename,
                ),
                aerial_image=self.aerial_image,
                main_title=DEFAULT_MAIN_TITLE,
                company_title=DEFAULT_COMPANY_TITLE,
            )

            filename = os.path.basename(path)
            self.file_var.set(f"✓ {filename}")
            self.set_status(f"✓ تم إنشاء التقرير بنجاح: {filename}")
            self._open_file(path)

        except Exception as exc:
            messagebox.showerror(
                "خطأ",
                f"تعذر إنشاء ملف PDF:\n\n{exc}",
            )
            self.set_status("✗ فشل إنشاء التقرير")

    def on_open_folder(self):
        try:
            os.makedirs(self.output, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(self.output)
            elif sys.platform == "darwin":
                os.system(f'open "{self.output}"')
            else:
                os.system(f'xdg-open "{self.output}"')
            self.set_status("✓ تم فتح مجلد التقارير")
        except Exception as exc:
            messagebox.showerror(
                "خطأ",
                f"تعذر فتح مجلد التقارير:\n{exc}",
            )

    @staticmethod
    def _open_file(path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception:
            pass


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        try:
            from tkinter import messagebox as mb
            mb.showerror("خطأ في تشغيل التطبيق", f"حدث خطأ أثناء تشغيل النظام:\n\n{traceback.format_exc()}")
        except Exception:
            pass
