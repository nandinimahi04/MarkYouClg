from app import db
from datetime import datetime

class ClassSession(db.Model):
    __tablename__ = 'class_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    division = db.Column(db.String(20))
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    roll_start = db.Column(db.Integer)
    roll_end = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='class_session', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'class_name': self.class_name,
            'department': self.department,
            'division': self.division,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'teacher_id': self.teacher_id,
            'roll_start': self.roll_start,
            'roll_end': self.roll_end,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'teacher': self.teacher.to_dict() if self.teacher else None
        }
    
    def __repr__(self):
        return f'<ClassSession {self.subject} - {self.class_name}>' 