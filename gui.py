import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import ollama
import threading
import sys
import webbrowser
from preprocess import load_and_preprocess, split_by_project_and_component
from ollama_functions import generate_summary_table
from webpage import build_html_report
from graphs import (
    generate_reports_per_component_bar,
    generate_resolution_pie,
    generate_grouped_bar_chart,
    generate_reports_over_time_line,
)


class StdoutRedirector:
    """Redirects console output to a tkinter Text widget."""

    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)

    def flush(self):
        pass


class BugReportGUI(tk.Tk):
    """The main GUI for the Bug Report Summarizer application."""

    def __init__(self):
        super().__init__()
        self.title("Bug Report Summarizer")
        self.geometry("800x850")  # Increased height for sort options
        self.csv_path = None
        self.model_map = {}
        self.cancel_event = threading.Event()
        self.output_path = os.path.join(os.getcwd(), "bug_report_summary.html")
        self.projects_data = []  # To store detailed project info for sorting

        # --- Main Frame ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 1. File Selection ---
        file_frame = ttk.LabelFrame(main_frame, text="1. Select CSV File")
        file_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.TOP)
        self.file_path_label = ttk.Label(file_frame, text="No file selected.")
        self.file_path_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.select_button = ttk.Button(file_frame, text="Select CSV", command=self.select_csv)
        self.select_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # --- 2. Column Selection ---
        column_frame = ttk.LabelFrame(main_frame, text="2. Map Columns")
        column_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.TOP)
        ttk.Label(column_frame, text="Project Column:").pack(side=tk.LEFT, padx=5, pady=5)
        self.project_col_var = tk.StringVar()
        self.project_col_dropdown = ttk.Combobox(column_frame, textvariable=self.project_col_var, state="readonly")
        self.project_col_dropdown.pack(side=tk.LEFT, padx=5, pady=5)
        self.project_col_dropdown.bind("<<ComboboxSelected>>", self.on_column_selection_change)

        ttk.Label(column_frame, text="Component Column:").pack(side=tk.LEFT, padx=5, pady=5)
        self.component_col_var = tk.StringVar()
        self.component_col_dropdown = ttk.Combobox(column_frame, textvariable=self.component_col_var, state="readonly")
        self.component_col_dropdown.pack(side=tk.LEFT, padx=5, pady=5)
        self.component_col_dropdown.bind("<<ComboboxSelected>>", self.on_column_selection_change)

        # --- Log Window ---
        log_frame = ttk.LabelFrame(main_frame, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.BOTTOM)
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10, background="#f1f3f6")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        sys.stdout = StdoutRedirector(self.log_text)

        # --- Progress Bar and Status Label ---
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(10, 5))
        self.progress_status_label = ttk.Label(progress_frame, text="", width=40)
        self.progress_status_label.pack(side=tk.LEFT, padx=(5, 0))
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.progress_percent_label = ttk.Label(progress_frame, text="", width=5)
        self.progress_percent_label.pack(side=tk.LEFT, padx=(0, 5))

        # --- Process and Cancel Buttons ---
        button_container = ttk.Frame(main_frame)
        button_container.pack(side=tk.BOTTOM, pady=5)
        self.process_button = ttk.Button(button_container, text="Generate Report", command=self.start_processing,
                                         state=tk.DISABLED)
        self.process_button.pack(side=tk.LEFT, padx=5)
        self.cancel_button = ttk.Button(button_container, text="Cancel", command=self.cancel_processing,
                                        state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        # --- Output File Selection ---
        output_frame = ttk.LabelFrame(main_frame, text="6. Select Output File")
        output_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        self.output_path_label = ttk.Label(output_frame, text=self.output_path)
        self.output_path_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.output_select_button = ttk.Button(output_frame, text="Save As...", command=self.select_output_path)
        self.output_select_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # --- Ollama Model Selection ---
        ollama_frame = ttk.LabelFrame(main_frame, text="5. Select Ollama Model")
        ollama_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        self.ollama_model_var = tk.StringVar()
        self.ollama_model_dropdown = ttk.Combobox(ollama_frame, textvariable=self.ollama_model_var, state="readonly")
        self.ollama_model_dropdown.pack(fill=tk.X, padx=5, pady=5)
        self.load_ollama_models()

        # --- AI Summary Options ---
        summary_options_frame = ttk.LabelFrame(main_frame, text="4. AI Summary Options")
        summary_options_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        ttk.Label(summary_options_frame, text="Chunk Size:").pack(side=tk.LEFT, padx=5, pady=5)
        self.chunk_size_var = tk.StringVar()
        self.chunk_size_dropdown = ttk.Combobox(summary_options_frame, textvariable=self.chunk_size_var, width=18)
        self.chunk_size_dropdown['values'] = ['5', '10', '25', '50', 'Process All at Once']
        self.chunk_size_dropdown.set('5')
        self.chunk_size_dropdown.pack(side=tk.LEFT, padx=5, pady=5)

        # --- Project Selection and Sorting ---
        project_frame = ttk.LabelFrame(main_frame, text="3. Select Projects to Process")
        project_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.TOP)

        # --- Sorting Controls ---
        sort_frame = ttk.Frame(project_frame)
        sort_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.sort_by_var = tk.StringVar(value="report_count")
        self.sort_order_var = tk.StringVar(value="desc")

        ttk.Label(sort_frame, text="Sort by:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(sort_frame, text="Reports", variable=self.sort_by_var, value="report_count",
                        command=self.sort_and_redisplay_projects).pack(side=tk.LEFT)
        ttk.Radiobutton(sort_frame, text="Components", variable=self.sort_by_var, value="component_count",
                        command=self.sort_and_redisplay_projects).pack(side=tk.LEFT)
        ttk.Radiobutton(sort_frame, text="Alphabetical", variable=self.sort_by_var, value="name",
                        command=self.sort_and_redisplay_projects).pack(side=tk.LEFT)

        ttk.Separator(sort_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Radiobutton(sort_frame, text="Descending", variable=self.sort_order_var, value="desc",
                        command=self.sort_and_redisplay_projects).pack(side=tk.LEFT)
        ttk.Radiobutton(sort_frame, text="Ascending", variable=self.sort_order_var, value="asc",
                        command=self.sort_and_redisplay_projects).pack(side=tk.LEFT)

        # --- Scrollable project list ---
        canvas_container = ttk.Frame(project_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_container, borderwidth=0, background="#ffffff")
        self.scrollable_content_frame = ttk.Frame(canvas)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas_frame_id = canvas.create_window((0, 0), window=self.scrollable_content_frame, anchor="nw")
        self.scrollable_content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_frame_id, width=e.width))
        self.project_vars = {}

    def on_column_selection_change(self, event=None):
        self.load_projects_and_components()

    def select_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.file_path_label.config(text=os.path.basename(file_path))
            self.csv_path = file_path
            self.load_csv_columns()
            self.load_projects_and_components()
            self.process_button.config(state=tk.NORMAL)

    def select_output_path(self):
        file_path = filedialog.asksaveasfilename(
            initialdir=os.getcwd(), title="Save HTML Report As", defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if file_path:
            self.output_path = file_path
            self.output_path_label.config(text=self.output_path)

    def load_csv_columns(self):
        try:
            df = pd.read_csv(self.csv_path, nrows=1)
            columns = list(df.columns)
            self.project_col_dropdown['values'] = columns
            self.component_col_dropdown['values'] = columns
            self.project_col_dropdown.config(state="readonly")
            self.component_col_dropdown.config(state="readonly")
            if 'Dyson Project List' in columns: self.project_col_var.set('Dyson Project List')
            if 'Component/s' in columns: self.component_col_var.set('Component/s')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read CSV columns: {e}")

    def load_projects_and_components(self):
        project_col = self.project_col_var.get()
        component_col = self.component_col_var.get()
        if not (self.csv_path and project_col and component_col): return

        try:
            print("Loading and preprocessing data for project list...")
            # Use a simplified version of the main preprocessor for speed
            df = pd.read_csv(self.csv_path, usecols=[project_col, component_col], low_memory=False)
            df.dropna(subset=[project_col], inplace=True)
            df[project_col] = df[project_col].astype(str).apply(lambda x: [p.strip() for p in x.split(',')])
            df = df.explode(project_col)

            df[component_col] = df[component_col].fillna('General')

            def clean_components(row):
                prefix = f"{row[project_col]}_"
                return [c.strip().replace(prefix, '') or 'General' for c in str(row[component_col]).split(',')]

            df['components'] = df.apply(clean_components, axis=1)

            self.projects_data = []
            grouped = df.groupby(project_col)
            for name, group in grouped:
                if not name: continue
                all_comps = group.explode('components')['components'].unique()
                self.projects_data.append({
                    'name': name,
                    'report_count': len(group),
                    'component_count': len(all_comps),
                    'components_preview': ", ".join(sorted(list(all_comps))[:3]),
                    'variable': tk.BooleanVar(value=True)
                })
            print("Finished processing data.")
            self.sort_and_redisplay_projects()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load projects: {e}")

    def sort_and_redisplay_projects(self):
        key = self.sort_by_var.get()
        is_reverse = self.sort_order_var.get() == "desc"
        self.projects_data.sort(key=lambda x: x[key], reverse=is_reverse)

        for widget in self.scrollable_content_frame.winfo_children():
            widget.destroy()

        self.project_vars = {}
        for proj in self.projects_data:
            self.project_vars[proj['name']] = proj['variable']
            label = (f"{proj['name']} (Reports: {proj['report_count']}, Components: {proj['component_count']}) "
                     f"- [{proj['components_preview']}{', ...' if proj['component_count'] > 3 else ''}]")
            ttk.Checkbutton(self.scrollable_content_frame, text=label, variable=proj['variable']).pack(anchor="w",
                                                                                                       padx=5, pady=2)

    def _bytes_to_gb(self, bytes_size):
        if not bytes_size: return "0.0 GB"
        return f"{bytes_size / (1024 ** 3):.1f} GB"

    def load_ollama_models(self):
        try:
            self.model_map = {}
            # Descriptions for specific models as requested
            model_descriptions = {
                "llama3.1:8b": " (Preferred for fast responses)",
                "llama3.3:70b-instruct-q2_K": " (Preferred for accurate responses)"
            }

            response = ollama.list()
            models_list = response.get('models', [])
            if not models_list:
                messagebox.showwarning("Warning", "No Ollama models found on the server.")
                return

            display_names = []
            default_model_display_name = None

            for model_obj in models_list:
                model_name = model_obj.get('model')
                if not model_name: continue

                model_size = model_obj.get('size', 0)
                description = model_descriptions.get(model_name, "")

                display_name = f"{model_name} ({self._bytes_to_gb(model_size)}){description}"

                self.model_map[display_name] = model_name
                display_names.append(display_name)

                # Check if the current model is the desired default
                if model_name == "llama3.1:8b":
                    default_model_display_name = display_name

            # Sort the display names alphabetically
            display_names.sort()
            self.ollama_model_dropdown['values'] = display_names

            # Set the default value
            if default_model_display_name:
                self.ollama_model_var.set(default_model_display_name)
            elif display_names:
                # Fallback to the first model if the preferred default isn't found
                self.ollama_model_var.set(display_names[0])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to Ollama: {e}")

    def start_processing(self):
        self.process_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.cancel_event.clear()
        self.log_text.delete(1.0, tk.END)
        self.after(0, self.update_progress, 0, "0%", "Starting...")
        threading.Thread(target=self.process_data, daemon=True).start()

    def cancel_processing(self):
        print("\n--- CANCELLATION REQUESTED ---")
        self.cancel_event.set()
        self.cancel_button.config(state=tk.DISABLED)

    def update_progress(self, value, percent_text, status_text):
        self.progress_bar['value'] = value
        self.progress_percent_label.config(text=percent_text)
        self.progress_status_label.config(text=status_text)

    def process_data(self):
        try:
            selected_projects = [p for p, v in self.project_vars.items() if v.get()]
            if not selected_projects:
                print("No projects selected. Aborting.")
                return

            print("Starting report generation...")
            self.after(0, self.update_progress, 0, "0%", "Loading data...")
            all_df = load_and_preprocess(self.csv_path, [self.component_col_var.get()], self.project_col_var.get())
            all_df = all_df[all_df[self.project_col_var.get()].isin(selected_projects)]
            print(f"Processing {len(all_df)} reports for {len(selected_projects)} selected project(s).")

            project_col = self.project_col_var.get()
            projects_list = all_df[project_col].unique()
            num_projects = len(projects_list)
            num_component_summaries = \
            all_df.explode('All_Components_List')[['All_Components_List', project_col]].drop_duplicates().shape[0]
            total_summary_tasks = num_projects + num_component_summaries

            project_graphs = {}
            for i, project_code in enumerate(projects_list):
                if self.cancel_event.is_set(): return
                status_text = f"Graphing: {project_code[:35]}..."
                progress_val = ((i + 1) / num_projects) * 10
                self.after(0, self.update_progress, progress_val, f"{int(progress_val)}%", status_text)
                project_df = all_df[all_df[project_col] == project_code]
                project_graphs[project_code] = {
                    'reports_per_component': generate_reports_per_component_bar(project_df),
                    'resolution_pie': generate_resolution_pie(project_df),
                    'priority_chart': generate_grouped_bar_chart(project_df, 'Priority'),
                    'severity_chart': generate_grouped_bar_chart(project_df, 'Severity'),
                    'reports_over_time': generate_reports_over_time_line(project_df),
                }

            if self.cancel_event.is_set(): return

            self.after(0, self.update_progress, 10, "10%", "Preparing AI summaries...")

            try:
                chunk_size_str = self.chunk_size_var.get()
                if chunk_size_str == 'Process All at Once':
                    chunk_size = len(all_df) + 1
                    print(f"Processing all {len(all_df)} reports in a single prompt.")
                else:
                    chunk_size = int(chunk_size_str)
                    print(f"Using a chunk size of {chunk_size} reports.")
            except (ValueError, TypeError):
                chunk_size = 5
                print(f"Invalid chunk size '{self.chunk_size_var.get()}'. Defaulting to {chunk_size}.")

            output_dir = './project_component_csvs'
            if not os.path.exists(output_dir): os.makedirs(output_dir)

            project_component_dfs = split_by_project_and_component(all_df, project_col, output_dir)
            actual_model_name = self.model_map.get(self.ollama_model_var.get(), 'llama3:8b')

            project_overall_summaries, project_component_summaries = generate_summary_table(
                all_df, project_component_dfs, project_col, actual_model_name, chunk_size, self.cancel_event, self,
                total_summary_tasks
            )

            if self.cancel_event.is_set(): return

            self.after(0, self.update_progress, 100, "100%", "Building HTML report...")
            html_report = build_html_report(project_overall_summaries, project_component_summaries, project_graphs,
                                            output_dir)

            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            print(f"\nReport saved to {os.path.abspath(self.output_path)}")

            self.after(100, self.processing_finished, self.output_path)

        except Exception as e:
            print(f"\n--- ERROR DURING PROCESSING ---\n{e}")
            self.after(0, self.update_progress, 0, "Error", "An error occurred.")
        finally:
            self.process_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)

    def processing_finished(self, output_file):
        if not self.cancel_event.is_set() and output_file:
            self.after(0, self.update_progress, 100, "100%", "Finished!")
            if messagebox.askyesno("Processing Complete", "Report generation finished. Open it now?"):
                webbrowser.open(f'file://{os.path.abspath(output_file)}')
        elif self.cancel_event.is_set():
            messagebox.showinfo("Cancelled", "Processing was cancelled by the user.")

        self.after(2000, self.update_progress, 0, "", "")