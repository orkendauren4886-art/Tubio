import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import torch
import os
import shutil
from PIL import Image, ImageTk
from ultralytics import YOLO

MODEL_PATH = 'best.pt'
V_WIDTH, V_HEIGHT = 800, 500 
BG_COLOR = "#1a1a1a"        
ACCENT_COLOR = "#00f2ff"    
DATA_BG = "#111111"

AREA_SMALL = 800   
AREA_MEDIUM = 3000 

class YoloDetectorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("PIPE SCANNER AI - NEURAL CORE v8.2")
        self.master.configure(bg=BG_COLOR)
        self.master.geometry(f"{V_WIDTH + 300}x{V_HEIGHT + 280}")
        self.master.resizable(False, False)

        self.running = False     
        self.frame_buffer = None 
        self.last_results = [] 

        self.base_dir = os.path.join(os.getcwd(), "INSPECTION_DATA")
        self.img_dir = os.path.join(self.base_dir, "screenshots")
        self.log_dir = os.path.join(self.base_dir, "logs")
        self._ensure_dirs()

        try:
            self.model = YOLO(MODEL_PATH).to('cuda' if torch.cuda.is_available() else 'cpu')
        except Exception as e:
            messagebox.showerror("Neural Error", f"Model not loaded: {e}")
            self.master.destroy()
            return

        self.camera_index_var = tk.IntVar(value=0)     
        self.fake_conf_var = tk.DoubleVar(value=50.0)  

        self._build_interface() 
        self._update_gui_loop() 

    def _ensure_dirs(self):
        os.makedirs(self.img_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

    def _clean_old_data(self):
        try:
            if os.path.exists(self.base_dir): 
                shutil.rmtree(self.base_dir)
            time.sleep(0.1)
            self._ensure_dirs()
        except: pass

    def get_size_info(self, w, h):
        area = w * h
        if area < AREA_SMALL:
            return "SMALL", (0, 255, 0)      
        elif area < AREA_MEDIUM:
            return "MEDIUM", (0, 255, 255)   
        else:
            return "LARGE", (0, 0, 255)      

    def _build_interface(self):
        top_container = tk.Frame(self.master, bg=BG_COLOR)
        top_container.pack(pady=15, padx=10, fill="x")

        self.video_frame = tk.Frame(top_container, width=V_WIDTH, height=V_HEIGHT, bg="black", highlightbackground=ACCENT_COLOR, highlightthickness=1)
        self.video_frame.pack(side="left")
        self.video_frame.pack_propagate(False)
        self.video_label = tk.Label(self.video_frame, bg="black")
        self.video_label.pack(expand=True, fill="both")

        self.data_panel = tk.Frame(top_container, width=260, height=V_HEIGHT, bg=DATA_BG, highlightbackground="#444", highlightthickness=1)
        self.data_panel.pack(side="right", padx=(10, 0))
        self.data_panel.pack_propagate(False)

        tk.Label(self.data_panel, text="AI ANALYSIS LOG", fg=ACCENT_COLOR, bg=DATA_BG, font=("Courier", 12, "bold")).pack(pady=10)
        self.coord_list = tk.Text(self.data_panel, bg="black", fg=ACCENT_COLOR, font=("Courier", 9), state="disabled", borderwidth=0)
        self.coord_list.pack(expand=True, fill="both", padx=5, pady=5)
        
        self.obj_count_label = tk.Label(self.data_panel, text="OBJECTS: 0", fg="white", bg=DATA_BG, font=("Arial", 12, "bold"))
        self.obj_count_label.pack(pady=10)

        ctrl_panel = tk.Frame(self.master, bg=BG_COLOR)
        ctrl_panel.pack(fill="x", padx=20)

        row1 = tk.Frame(ctrl_panel, bg=BG_COLOR)
        row1.pack(fill="x", pady=5)
        self.btn_start = tk.Button(row1, text="INITIALIZE AI SCAN", bg="#2ecc71", font=("Arial", 14, "bold"), width=30, height=2, command=self.start_detection)
        self.btn_start.pack(side="left", padx=10)
        self.btn_stop = tk.Button(row1, text="TERMINATE", bg="#e74c3c", fg="white", font=("Arial", 14, "bold"), width=15, height=2, command=self.stop_detection, state="disabled")
        self.btn_stop.pack(side="left")

        row2 = tk.Frame(ctrl_panel, bg=BG_COLOR)
        row2.pack(fill="x", pady=10)
        
        tk.Label(row2, text="CAM ID:", fg="white", bg=BG_COLOR).pack(side="left")
        tk.Entry(row2, textvariable=self.camera_index_var, width=3, font=("Arial", 12)).pack(side="left", padx=5)

        tk.Label(row2, text="SENSITIVITY:", fg=ACCENT_COLOR, bg=BG_COLOR, font=("Arial", 10, "bold")).pack(side="left", padx=(20, 5))
        ttk.Scale(row2, from_=0, to=100, variable=self.fake_conf_var, length=200).pack(side="left")

        tk.Button(row2, text="📸 SNAPSHOT", bg="#3498db", fg="white", font=("Arial", 10, "bold"), width=12, height=2, command=self.take_screenshot).pack(side="left", padx=(30, 5))
        tk.Button(row2, text="💾 REPORT", bg="#f1c40f", fg="black", font=("Arial", 10, "bold"), width=12, height=2, command=self.save_defect_log).pack(side="left")

    def draw_tech_marker(self, frame, x1, y1, x2, y2, cx, cy, label, color):
        L, t = 20, 2
        cv2.line(frame, (int(x1), int(y1)), (int(x1)+L, int(y1)), color, t)
        cv2.line(frame, (int(x1), int(y1)), (int(x1), int(y1)+L), color, t)
        cv2.line(frame, (int(x2), int(y2)), (int(x2)-L, int(y2)), color, t)
        cv2.line(frame, (int(x2), int(y2)), (int(x2), int(y2)-L), color, t)
        
        cv2.circle(frame, (cx, cy), 4, color, -1)
        cv2.putText(frame, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def detection_worker(self):
        cap = cv2.VideoCapture(self.camera_index_var.get())
        while self.running:
            success, frame = cap.read()
            if not success: break
            
            real_conf = self.fake_conf_var.get() / 166.6
            if real_conf < 0.01: real_conf = 0.01

            results = self.model.predict(frame, conf=real_conf, verbose=False)
            boxes = results[0].boxes
            
            temp_results = []
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                w, h = int(x2 - x1), int(y2 - y1)
                cx, cy = int(x1 + w/2), int(y1 + h/2)
                
                category, color = self.get_size_info(w, h)
                temp_results.append((cx, cy, w, h, category))
                
                self.draw_tech_marker(frame, x1, y1, x2, y2, cx, cy, f"#{i+1} {category}", color)

            self.last_results = temp_results
            self.frame_buffer = frame
            time.sleep(0.01)
        cap.release()

    def _update_gui_loop(self):
        if self.running and self.frame_buffer is not None:
            img = cv2.cvtColor(self.frame_buffer, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img).resize((V_WIDTH, V_HEIGHT), Image.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)
            self.video_label.config(image=img_tk)
            self.video_label.image = img_tk
            
            self.coord_list.config(state="normal")
            self.coord_list.delete("1.0", tk.END)
            for i, (cx, cy, w, h, cat) in enumerate(self.last_results):
                self.coord_list.insert(tk.END, f"[{i+1}] {cat}\n Sz: {w}x{h}\n Pos: {cx},{cy}\n\n")
            self.coord_list.config(state="disabled")
            self.obj_count_label.config(text=f"OBJECTS: {len(self.last_results)}")
        
        self.master.after(30, self._update_gui_loop)

    def take_screenshot(self):
        if self.frame_buffer is not None:
            ts = time.strftime("%H%M%S")
            path = os.path.join(self.img_dir, f"SNAP_{ts}.jpg")
            cv2.imwrite(path, self.frame_buffer)
            messagebox.showinfo("AI SYSTEM", "Snapshot saved to vault.")

    def save_defect_log(self):
        if not self.last_results:
            messagebox.showwarning("AI SYSTEM", "No data to record.")
            return
            
        path = os.path.join(self.log_dir, "inspection_report.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n--- SESSION: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            for i, (cx, cy, w, h, cat) in enumerate(self.last_results):
                f.write(f"ID:{i+1} | SIZE:{cat} | DIM:{w}x{h}px | POS:{cx},{cy}\n")
        messagebox.showinfo("AI SYSTEM", "Report successfully exported.")

    def start_detection(self):
        if not self.running:
            self._clean_old_data()
            self.running = True
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            threading.Thread(target=self.detection_worker, daemon=True).start()

    def stop_detection(self):
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = YoloDetectorApp(root)
    root.mainloop()
