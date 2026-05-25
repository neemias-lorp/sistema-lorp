#!/usr/bin/env python3
from app import app, db, User, Pergunta, Descoberta
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                email='contato@lorp.org'
            )
            db.session.add(admin)
        
        if Descoberta.query.count() == 0:
            descobertas = [
                {"titulo": "Linear A - Tabela AB 131", "descricao": "Sequência A-SA-SA-RA-ME explicada por reduplicação enfática", "protocolo": "BN: 2026040275033", "previsibilidade": "87%", "categoria": "Paleografia", "icone": "📜"},
                {"titulo": "Manuscrito Voynich", "descricao": "Análise estatística com matriz de transição de 77,8%", "previsibilidade": "77,8%", "categoria": "Paleografia", "icone": "📖"},
                {"titulo": "Vale do Indo", "descricao": "Regra de reprodução final S[1] = S[n]", "categoria": "Paleografia", "icone": "🏺"},
                {"titulo": "Onto-Álgebra LORP", "descricao": "Unificação do Ser e do Devir", "protocolo": "BN: 2026041365220", "categoria": "Teoria", "icone": "🧬"}
            ]
            for d in descobertas:
                db.session.add(Descoberta(**d))
        
        db.session.commit()
        print("✅ Banco inicializado! Usuário: admin / senha: admin123")

if __name__ == '__main__':
    init_db()
