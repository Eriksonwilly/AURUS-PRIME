
class PaymentSystem:
    def login_user(self, email, password):
        if email == "demo" and password == "demo":
            return {"success": True, "user": {"email": "demo", "name": "Demo User", "plan": "gratuito"}}
        if email == "admin" and password == "admin":
            return {"success": True, "user": {"email": "admin", "name": "Admin", "plan": "premium"}}
        return {"success": False, "message": "Credenciales inválidas"}
    
    def register_user(self, email, password, name):
        return {"success": True, "message": "Usuario registrado"}
    
    def upgrade_plan(self, email, plan, method):
        return {"success": True, "message": "Plan actualizado", "auto_confirmed": True}

payment_system = PaymentSystem()
