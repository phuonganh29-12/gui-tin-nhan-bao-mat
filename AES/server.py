import socket
import json
import base64
import threading
import os
import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog
from PIL import Image, ImageTk
from io import BytesIO
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from crypto_utils import (
    load_rsa_keys,
    encrypt_aes_key,
    decrypt_aes_key,
    sign_data,
    verify_signature,
    encrypt_message,
    decrypt_message,
    compute_hash
)
from config import HOST, PORT

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class GiaoDienNguoiNhan:
    def __init__(self, root):
        self.root = root
        self.root.title("Ứng dụng nhận tin - Bob")
        self.root.geometry("600x580")
        self.root.resizable(False, False)

        self.frame = ctk.CTkFrame(master=self.root)
        self.frame.pack(padx=20, pady=20, fill="both", expand=True)

        self.label = ctk.CTkLabel(master=self.frame, text="Bob Chat", font=("Arial", 20, "bold"))
        self.label.pack(pady=10)

        self.khu_vuc_chat = ctk.CTkTextbox(master=self.frame, width=550, height=300, corner_radius=10)
        self.khu_vuc_chat.pack(pady=10)
        self.khu_vuc_chat.configure(state="disabled")

        self.nhap_frame = ctk.CTkFrame(master=self.frame)
        self.nhap_frame.pack(pady=5, fill="x")

        self.o_nhap_tin = ctk.CTkEntry(master=self.nhap_frame, width=300, placeholder_text="Nhập tin nhắn...")
        self.o_nhap_tin.pack(side="left", padx=5, pady=5)

        self.nut_emoji = ctk.CTkButton(master=self.nhap_frame, text="😊", width=30, command=self.hien_bang_emoji)
        self.nut_emoji.pack(side="left", padx=2)

        self.nut_gui = ctk.CTkButton(master=self.nhap_frame, text="Gửi", command=self.gui_tin_nhan)
        self.nut_gui.pack(side="left", padx=2)

        self.nut_file = ctk.CTkButton(master=self.nhap_frame, text="📎", width=30, command=self.gui_file)
        self.nut_file.pack(side="left", padx=2)

        self.popup_emoji = None
        self.danh_sach_anh = []

        self.ket_noi = None
        self.server_socket = None
        self.khoa_aes = None
        self.khoa_cong_khai_nguoi_gui = None
        self.dang_chay = True

        self.khoa_rieng, self.khoa_cong_khai = load_rsa_keys("bob")
        if self.khoa_rieng is None or self.khoa_cong_khai is None:
            self.ghi_nhat_ky("Lỗi: Không thể tải khóa RSA")
            return

        self.root.after(100, self.bat_dau_lang_nghe)

    def lay_thoi_gian(self):
        return datetime.now().strftime("%H:%M")

    def ghi_nhat_ky(self, thong_diep):
        self.khu_vuc_chat.configure(state="normal")
        self.khu_vuc_chat.insert("end", thong_diep + "\n")
        self.khu_vuc_chat.configure(state="disabled")
        self.khu_vuc_chat.yview("end")

    def hien_anh_nho(self, du_lieu_anh):
        try:
            img = Image.open(BytesIO(du_lieu_anh)).resize((100, 100))
            img_tk = ImageTk.PhotoImage(img)
            self.danh_sach_anh.append(img_tk)
            self.khu_vuc_chat.image_create("end", image=img_tk)
            self.khu_vuc_chat.insert("end", f"  ({self.lay_thoi_gian()})\n")
        except Exception as e:
            self.ghi_nhat_ky(f"⚠️ Không thể hiển thị ảnh: {e}")

    def hien_bang_emoji(self):
        if self.popup_emoji and self.popup_emoji.winfo_exists():
            self.popup_emoji.destroy()
            return

        self.popup_emoji = ctk.CTkToplevel(self.root)
        self.popup_emoji.title("Chọn emoji")
        self.popup_emoji.geometry("220x120")
        self.popup_emoji.resizable(False, False)

        emoji_list = ["😀", "😍", "😭", "😡", "😂", "❤️", "👍", "🎉"]

        for i, emo in enumerate(emoji_list):
            btn = ctk.CTkButton(self.popup_emoji, text=emo, width=40, command=lambda e=emo: self.chen_emoji(e))
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)

    def chen_emoji(self, emoji):
        current = self.o_nhap_tin.get()
        self.o_nhap_tin.delete(0, "end")
        self.o_nhap_tin.insert(0, current + emoji)
        if self.popup_emoji:
            self.popup_emoji.destroy()

    def bat_dau_lang_nghe(self):
        thread = threading.Thread(target=self.khoi_dong_server, daemon=True)
        thread.start()

    def khoi_dong_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.settimeout(None)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(1)
            self.ghi_nhat_ky("💬 Đang chờ Alice kết nối...")
            self.cho_ket_noi()
        except Exception as e:
            self.ghi_nhat_ky(f"Lỗi khởi động server: {e}")

    def cho_ket_noi(self):
        while self.dang_chay:
            try:
                if not self.server_socket:
                    break
                self.ket_noi, dia_chi = self.server_socket.accept()
                self.ket_noi.settimeout(None)
                self.ghi_nhat_ky(f"🔗 Đã kết nối với {dia_chi}")

                self.khoa_cong_khai_nguoi_gui = RSA.import_key(self.ket_noi.recv(4096))
                self.ket_noi.send(self.khoa_cong_khai.export_key())

                du_lieu = json.loads(self.ket_noi.recv(4096).decode())
                khoa_aes_ma_hoa = base64.b64decode(du_lieu['encrypted_aes_key'])
                chu_ky = base64.b64decode(du_lieu['signature'])
                sieu_du_lieu = du_lieu['metadata'].encode()

                if not verify_signature(sieu_du_lieu, chu_ky, self.khoa_cong_khai_nguoi_gui):
                    self.ghi_nhat_ky("❌ Chữ ký metadata không hợp lệ")
                    self.ket_noi.send(json.dumps({"status": "NACK", "error": "Invalid signature"}).encode())
                    self.ket_noi.close()
                    continue

                self.khoa_aes = decrypt_aes_key(khoa_aes_ma_hoa, self.khoa_rieng)
                self.ghi_nhat_ky("🔐 Đã nhận và giải mã khóa AES")

                self.nhan_tin_nhan()

            except Exception as e:
                self.ghi_nhat_ky(f"Lỗi khi kết nối: {e}")
                if self.ket_noi:
                    self.ket_noi.close()

    def nhan_tin_nhan(self):
        def vong_nhan():
            while self.dang_chay and self.ket_noi:
                try:
                    du_lieu = self.ket_noi.recv(4096 * 10)
                    if not du_lieu:
                        raise ConnectionError("⛔ Kết nối đã bị đóng")
                    du_lieu = json.loads(du_lieu.decode())

                    if "cipher" in du_lieu:
                        iv = base64.b64decode(du_lieu["iv"])
                        ban_ma = base64.b64decode(du_lieu["cipher"])
                        ma_bam = du_lieu["hash"]
                        chu_ky = base64.b64decode(du_lieu["signature"])

                        if not verify_signature(iv + ban_ma, chu_ky, self.khoa_cong_khai_nguoi_gui):
                            self.ghi_nhat_ky("❌ Chữ ký tin nhắn không hợp lệ")
                            self.ket_noi.send(json.dumps({"status": "NACK", "error": "Invalid message signature"}).encode())
                            continue

                        if compute_hash(iv, ban_ma) != ma_bam:
                            self.ghi_nhat_ky("⚠️ Kiểm tra toàn vẹn thất bại")
                            self.ket_noi.send(json.dumps({"status": "NACK", "error": "Integrity check failed"}).encode())
                            continue

                        try:
                            thong_diep = decrypt_message(iv, ban_ma, self.khoa_aes)
                            du_lieu_nhi_phan = thong_diep.encode("latin1")
                            self.hien_anh_nho(du_lieu_nhi_phan)
                        except Exception as err:
                            self.ghi_nhat_ky(f"Alice: {thong_diep} ({self.lay_thoi_gian()})")

                        self.ket_noi.send(json.dumps({"status": "ACK"}).encode())

                except Exception as e:
                    self.ghi_nhat_ky(f"Lỗi nhận tin: {e}")
                    break

        threading.Thread(target=vong_nhan, daemon=True).start()

    def gui_tin_nhan(self):
        try:
            thong_diep = self.o_nhap_tin.get()
            if not thong_diep or not self.ket_noi or not self.khoa_aes or not self.khoa_cong_khai_nguoi_gui:
                self.ghi_nhat_ky("⚠️ Không thể gửi tin (thiếu kết nối hoặc khóa)")
                return

            iv, ban_ma = encrypt_message(thong_diep, self.khoa_aes)
            ma_bam = compute_hash(iv, ban_ma)
            chu_ky = sign_data(iv + ban_ma, self.khoa_rieng)

            du_lieu = {
                "iv": base64.b64encode(iv).decode(),
                "cipher": base64.b64encode(ban_ma).decode(),
                "hash": ma_bam,
                "signature": base64.b64encode(chu_ky).decode()
            }
            self.ket_noi.send(json.dumps(du_lieu).encode())
            self.ghi_nhat_ky(f"Bob: {thong_diep} ({self.lay_thoi_gian()})")
            self.o_nhap_tin.delete(0, "end")
        except Exception as e:
            self.ghi_nhat_ky(f"Lỗi khi gửi tin: {e}")

    def gui_file(self):
        if not self.ket_noi or not self.khoa_aes:
            self.ghi_nhat_ky("⚠️ Không thể gửi file (chưa kết nối)")
            return

        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        try:
            with open(file_path, "rb") as f:
                noi_dung = f.read()
            du_lieu_ma_hoa = noi_dung.decode("latin1")
            iv, ban_ma = encrypt_message(du_lieu_ma_hoa, self.khoa_aes)
            ma_bam = compute_hash(iv, ban_ma)
            chu_ky = sign_data(iv + ban_ma, self.khoa_rieng)

            file_data = {
                "iv": base64.b64encode(iv).decode(),
                "cipher": base64.b64encode(ban_ma).decode(),
                "hash": ma_bam,
                "signature": base64.b64encode(chu_ky).decode()
            }
            self.ket_noi.send(json.dumps(file_data).encode())
            ten_file = os.path.basename(file_path)
            self.ghi_nhat_ky(f"📎 Bob đã gửi file: {ten_file} ({self.lay_thoi_gian()})")
        except Exception as e:
            self.ghi_nhat_ky(f"Lỗi khi gửi file: {e}")

    def on_closing(self):
        self.dang_chay = False
        if self.ket_noi:
            self.ket_noi.close()
        if self.server_socket:
            self.server_socket.close()
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = GiaoDienNguoiNhan(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
