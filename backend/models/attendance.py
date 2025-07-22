from app import db
from datetime import datetime

class Attendance(db.Model):
    __tablename__ = 'attendances'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_session_id = db.Column(db.Integer, db.ForeignKey('class_sessions.id'), nullable=False)
    status = db.Column(db.String(20), default='present')  # 'present', 'absent', 'late'
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Teacher who recorded
    notes = db.Column(db.Text)
    
    # Relationships with explicit foreign keys
    user = db.relationship('User', foreign_keys=[user_id], backref='attendances')
    class_session = db.relationship('ClassSession', backref='attendances')
    recorder = db.relationship('User', foreign_keys=[recorded_by], backref='recorded_attendances')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'class_session_id': self.class_session_id,
            'status': self.status,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'recorded_by': self.recorded_by,
            'notes': self.notes,
            'user': self.user.to_dict() if self.user else None,
            'class_session': self.class_session.to_dict() if self.class_session else None
        }
    
    def __repr__(self):
        return f'<Attendance {self.user_id} - {self.status}>' 