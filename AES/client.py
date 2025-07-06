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
from crypto_utils import load_rsa_keys, encrypt_aes_key, sign_data, encrypt_message, compute_hash, decrypt_message
from config import HOST, PORT

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class GiaoDienNguoiGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Ứng dụng nhắn tin bảo mật - Alice")
        self.root.geometry("600x580")
        self.root.resizable(False, False)

        self.frame = ctk.CTkFrame(master=self.root)
        self.frame.pack(padx=20, pady=20, fill="both", expand=True)

        self.label = ctk.CTkLabel(master=self.frame, text="Alice Chat", font=("Arial", 20, "bold"))
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

        self.ket_noi = None
        self.khoa_cong_khai_nguoi_nhan = None
        self.khoa_aes = None
        self.so_lan_thu = 0
        self.so_lan_thu_toi_da = 5
        self.dang_chay = True
        self.danh_sach_anh = []

        self.khoa_rieng, self.khoa_cong_khai = load_rsa_keys("alice")
        if self.khoa_rieng is None or self.khoa_cong_khai is None:
            self.ghi_nhat_ky("❌ Không thể tải khóa RSA")
            return

        self.root.after(100, self.bat_dau_ket_noi_thread)

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

    def bat_dau_ket_noi_thread(self):
        threading.Thread(target=self.ket_noi_voi_nguoi_nhan, daemon=True).start()

    def ket_noi_voi_nguoi_nhan(self):
        while self.so_lan_thu < self.so_lan_thu_toi_da and self.dang_chay:
            try:
                self.ket_noi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.ket_noi.settimeout(None)
                self.ket_noi.connect((HOST, PORT))
                self.ghi_nhat_ky("🔗 Đã kết nối với Bob")
                self.so_lan_thu = 0

                self.ket_noi.send(self.khoa_cong_khai.export_key())
                khoa_nhan = self.ket_noi.recv(4096)
                self.khoa_cong_khai_nguoi_nhan = RSA.import_key(khoa_nhan)
                self.ghi_nhat_ky("🔐 Đã trao đổi khóa công khai")

                self.khoa_aes = get_random_bytes(32)
                khoa_aes_ma_hoa = encrypt_aes_key(self.khoa_aes, self.khoa_cong_khai_nguoi_nhan)
                sieu_du_lieu = f"UserID:Alice|SessionID:123".encode()
                chu_ky = sign_data(sieu_du_lieu, self.khoa_rieng)

                du_lieu = {
                    "encrypted_aes_key": base64.b64encode(khoa_aes_ma_hoa).decode(),
                    "signature": base64.b64encode(chu_ky).decode(),
                    "metadata": sieu_du_lieu.decode()
                }
                self.ket_noi.send(json.dumps(du_lieu).encode())
                self.ghi_nhat_ky("📤 Đã gửi khóa AES")

                threading.Thread(target=self.nhan_tin_nhan, daemon=True).start()
                break
            except Exception as e:
                self.so_lan_thu += 1
                self.ghi_nhat_ky(f"⏳ Thử kết nối ({self.so_lan_thu}/{self.so_lan_thu_toi_da}) thất bại")

    def nhan_tin_nhan(self):
        while self.dang_chay and self.ket_noi:
            try:
                du_lieu = self.ket_noi.recv(4096 * 10)
                if not du_lieu:
                    raise ConnectionError("🔌 Mất kết nối với server")
                du_lieu = json.loads(du_lieu.decode())

                if du_lieu.get("status") == "ACK":
                    self.ghi_nhat_ky("✅ Server xác nhận tin nhắn")
                elif "cipher" in du_lieu:
                    iv = base64.b64decode(du_lieu['iv'])
                    ban_ma = base64.b64decode(du_lieu['cipher'])
                    thong_diep = decrypt_message(iv, ban_ma, self.khoa_aes)

                    # Nếu là ảnh base64, lưu và hiển thị
                    try:
                        du_lieu_nhi_phan = thong_diep.encode("latin1")
                        self.hien_anh_nho(du_lieu_nhi_phan)
                    except:
                        self.ghi_nhat_ky(f"Bob: {thong_diep} ({self.lay_thoi_gian()})")
            except Exception as e:
                self.ghi_nhat_ky(f"Lỗi khi nhận tin: {e}")
                break
        if self.ket_noi:
            self.ket_noi.close()

    def gui_tin_nhan(self):
        try:
            thong_diep = self.o_nhap_tin.get()
            if not thong_diep:
                return
            if not self.khoa_aes or not self.khoa_cong_khai_nguoi_nhan or not self.ket_noi:
                self.ghi_nhat_ky("⚠️ Kết nối chưa sẵn sàng")
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
            self.ghi_nhat_ky(f"Alice: {thong_diep} ({self.lay_thoi_gian()})")
            self.o_nhap_tin.delete(0, "end")
        except Exception as e:
            self.ghi_nhat_ky(f"Lỗi gửi tin: {e}")

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
            try:
                du_lieu_ma_hoa = noi_dung.decode("latin1")  # giữ nhị phân nguyên gốc
            except:
                self.ghi_nhat_ky("⚠️ Không thể mã hóa ảnh")
                return

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
            self.ghi_nhat_ky(f"📎 Alice đã gửi file: {ten_file} ({self.lay_thoi_gian()})")
        except Exception as e:
            self.ghi_nhat_ky(f"Lỗi khi gửi file: {e}")

    def dong_ung_dung(self):
        self.dang_chay = False
        if self.ket_noi:
            self.ket_noi.close()
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = GiaoDienNguoiGui(root)
    root.protocol("WM_DELETE_WINDOW", app.dong_ung_dung)
    root.mainloop()
