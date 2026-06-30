#!/usr/bin/env python3
"""Sistema de pagos simple para AURUS PRIME / CONSORCIO DEJ."""

import json
import os
import hashlib
import datetime
from typing import Dict, List

class SimplePaymentSystem:
    def __init__(self):
        self.users_file = "users.json"
        self.payments_file = "payments.json"
        self.admin_credentials = {"usuario": "admin", "clave": "admin123"}
        self.load_data()
        self.create_default_admin()

    def create_default_admin(self):
        admin_email = "admin@consorciodej.com"
        if admin_email not in self.users:
            self.users[admin_email] = {
                "email": admin_email,
                "password": self.hash_password("admin123"),
                "name": "admin",
                "plan": "empresarial",
                "created_at": datetime.datetime.now().isoformat(),
                "expires_at": None,
            }
            self.save_data()
        elif self.users[admin_email]["plan"] != "empresarial":
            self.users[admin_email]["plan"] = "empresarial"
            self.users[admin_email]["expires_at"] = None
            self.save_data()

    def load_data(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, "r", encoding="utf-8") as f:
                self.users = json.load(f)
        else:
            self.users = {}
        if os.path.exists(self.payments_file):
            with open(self.payments_file, "r", encoding="utf-8") as f:
                self.payments = json.load(f)
        else:
            self.payments = []

    def save_data(self):
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)
        with open(self.payments_file, "w", encoding="utf-8") as f:
            json.dump(self.payments, f, indent=2, ensure_ascii=False)

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, email: str, password: str, name: str) -> Dict:
        if email in self.users:
            return {"success": False, "message": "El email ya está registrado"}
        self.users[email] = {
            "email": email,
            "password": self.hash_password(password),
            "name": name,
            "plan": "gratuito",
            "created_at": datetime.datetime.now().isoformat(),
            "expires_at": None,
        }
        self.save_data()
        return {"success": True, "message": "Usuario registrado exitosamente"}

    def login_user(self, email: str, password: str) -> Dict:
        if email == "admin" and password == "admin123":
            return {
                "success": True,
                "user": {
                    "email": "admin",
                    "name": "Administrador",
                    "plan": "empresarial",
                    "expires_at": None,
                    "is_admin": True,
                },
            }
        user_found = self.users.get(email)
        if not user_found:
            for user_data in self.users.values():
                if user_data.get("name", "").lower() == email.lower():
                    user_found = user_data
                    break
        if not user_found:
            return {"success": False, "message": "Usuario no encontrado"}
        if user_found["password"] != self.hash_password(password):
            return {"success": False, "message": "Contraseña incorrecta"}
        return {
            "success": True,
            "user": {
                "email": user_found["email"],
                "name": user_found["name"],
                "plan": user_found["plan"],
                "expires_at": user_found["expires_at"],
                "is_admin": user_found.get("email") == "admin@consorciodej.com",
            },
        }

    def upgrade_plan(self, email: str, plan: str, payment_method: str) -> Dict:
        if email not in self.users:
            return {"success": False, "message": "Usuario no encontrado"}
        if email in ("admin", "admin@consorciodej.com"):
            self.users[email]["plan"] = plan
            self.users[email]["expires_at"] = None
            self.save_data()
            return {"success": True, "message": f"Plan {plan} activado para administrador", "admin_access": True}
        plan_info = {"premium": {"price": 29.99}, "empresarial": {"price": 99.99}}
        if plan not in plan_info:
            return {"success": False, "message": "Plan no válido"}
        payment = {
            "id": f"PAY_{len(self.payments) + 1:06d}",
            "email": email,
            "plan": plan,
            "amount": plan_info[plan]["price"],
            "payment_method": payment_method,
            "status": "pendiente",
            "created_at": datetime.datetime.now().isoformat(),
            "instructions": self.get_payment_instructions(payment_method, plan_info[plan]["price"]),
        }
        self.payments.append(payment)
        self.users[email]["plan"] = plan
        self.users[email]["payment_pending"] = payment["id"]
        if payment_method in ("yape", "plin", "paypal"):
            confirm = self.confirm_payment(payment["id"])
            if confirm["success"]:
                return {
                    "success": True,
                    "payment_id": payment["id"],
                    "instructions": payment["instructions"],
                    "amount": payment["amount"],
                    "auto_confirmed": True,
                    "message": "Pago confirmado automáticamente",
                }
        self.save_data()
        return {
            "success": True,
            "payment_id": payment["id"],
            "instructions": payment["instructions"],
            "amount": payment["amount"],
        }

    def get_payment_instructions(self, method: str, amount: float) -> str:
        pen = amount * 3.7
        if method == "paypal":
            return f"Pago PayPal: ${amount:.2f} USD — paypal.me/consorciodej"
        if method == "transferencia":
            return f"Transferencia BCP: S/{pen:.2f} PEN — Cuenta CONSORCIO DEJ SAC"
        if method == "yape":
            return f"Yape: S/{pen:.2f} PEN — +51 999 888 777"
        if method == "plin":
            return f"PLIN: S/{pen:.2f} PEN — +51 999 888 777"
        return f"Efectivo: S/{pen:.2f} PEN — contacto +51 999 888 777"

    def confirm_payment(self, payment_id: str) -> Dict:
        payment = next((p for p in self.payments if p["id"] == payment_id), None)
        if not payment:
            return {"success": False, "message": "Pago no encontrado"}
        if payment["status"] == "confirmado":
            return {"success": False, "message": "Pago ya confirmado"}
        payment["status"] = "confirmado"
        payment["confirmed_at"] = datetime.datetime.now().isoformat()
        email = payment["email"]
        if email in self.users:
            self.users[email]["plan"] = payment["plan"]
            self.users[email]["payment_pending"] = None
            expires = datetime.datetime.now() + datetime.timedelta(days=30)
            self.users[email]["expires_at"] = expires.isoformat()
            self.save_data()
            return {"success": True, "message": f"Plan {payment['plan']} activado", "user_email": email, "plan": payment["plan"]}
        return {"success": False, "message": "Usuario no encontrado"}

    def get_user_plan(self, email: str) -> Dict:
        if email not in self.users:
            return {"plan": "gratuito", "expires_at": None}
        user = self.users[email]
        return {"plan": user["plan"], "expires_at": user["expires_at"], "payment_pending": user.get("payment_pending")}

    def check_plan_access(self, email: str, required_plan: str) -> bool:
        if email in ("admin", "admin@consorciodej.com"):
            return True
        user_plan = self.get_user_plan(email)
        hierarchy = {"gratuito": 0, "premium": 1, "empresarial": 2}
        if user_plan["expires_at"]:
            try:
                if datetime.datetime.now() > datetime.datetime.fromisoformat(user_plan["expires_at"]):
                    return False
            except ValueError:
                pass
        return hierarchy.get(user_plan["plan"], 0) >= hierarchy.get(required_plan, 0)


payment_system = SimplePaymentSystem()
