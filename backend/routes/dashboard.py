from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from models.user import User
from models.attendance import Attendance
from models.class_session import ClassSession
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get date range (default to last 30 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        if request.args.get('start_date'):
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
        if request.args.get('end_date'):
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
        
        if user.role == 'student':
            # Student dashboard stats
            attendances = Attendance.query.join(ClassSession).filter(
                and_(
                    Attendance.user_id == current_user_id,
                    ClassSession.date >= start_date,
                    ClassSession.date <= end_date
                )
            ).all()
            
            total_sessions = len(attendances)
            present_count = len([a for a in attendances if a.status == 'present'])
            absent_count = len([a for a in attendances if a.status == 'absent'])
            late_count = len([a for a in attendances if a.status == 'late'])
            
            attendance_percentage = (present_count / total_sessions * 100) if total_sessions > 0 else 0
            
            # Get recent attendance
            recent_attendances = Attendance.query.join(ClassSession).filter(
                and_(
                    Attendance.user_id == current_user_id,
                    ClassSession.date >= end_date - timedelta(days=7)
                )
            ).order_by(ClassSession.date.desc()).limit(5).all()
            
            return jsonify({
                'total_sessions': total_sessions,
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'attendance_percentage': round(attendance_percentage, 2),
                'recent_attendances': [att.to_dict() for att in recent_attendances],
                'warning': attendance_percentage < 75
            }), 200
        
        elif user.role == 'teacher':
            # Teacher dashboard stats
            sessions = ClassSession.query.filter(
                and_(
                    ClassSession.teacher_id == current_user_id,
                    ClassSession.date >= start_date,
                    ClassSession.date <= end_date
                )
            ).all()
            
            total_sessions = len(sessions)
            total_students = 0
            total_present = 0
            total_absent = 0
            
            for session in sessions:
                attendances = Attendance.query.filter_by(class_session_id=session.id).all()
                total_students += len(attendances)
                total_present += len([a for a in attendances if a.status == 'present'])
                total_absent += len([a for a in attendances if a.status == 'absent'])
            
            avg_attendance = (total_present / total_students * 100) if total_students > 0 else 0
            
            # Get recent sessions
            recent_sessions = ClassSession.query.filter(
                and_(
                    ClassSession.teacher_id == current_user_id,
                    ClassSession.date >= end_date - timedelta(days=7)
                )
            ).order_by(ClassSession.date.desc()).limit(5).all()
            
            return jsonify({
                'total_sessions': total_sessions,
                'total_students': total_students,
                'total_present': total_present,
                'total_absent': total_absent,
                'average_attendance': round(avg_attendance, 2),
                'recent_sessions': [session.to_dict() for session in recent_sessions]
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/attendance-trend', methods=['GET'])
@jwt_required()
def get_attendance_trend():
    """Get attendance trend over time"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get date range (default to last 30 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        if request.args.get('start_date'):
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
        if request.args.get('end_date'):
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
        
        if user.role == 'student':
            # Student attendance trend
            attendances = db.session.query(
                ClassSession.date,
                func.count(Attendance.id).label('total'),
                func.sum(func.case([(Attendance.status == 'present', 1)], else_=0)).label('present')
            ).join(Attendance).filter(
                and_(
                    Attendance.user_id == current_user_id,
                    ClassSession.date >= start_date,
                    ClassSession.date <= end_date
                )
            ).group_by(ClassSession.date).order_by(ClassSession.date).all()
            
            trend_data = []
            for date, total, present in attendances:
                percentage = (present / total * 100) if total > 0 else 0
                trend_data.append({
                    'date': date.isoformat(),
                    'total': total,
                    'present': present,
                    'percentage': round(percentage, 2)
                })
            
            return jsonify({
                'trend_data': trend_data
            }), 200
        
        elif user.role == 'teacher':
            # Teacher attendance trend
            sessions_data = db.session.query(
                ClassSession.date,
                func.count(Attendance.id).label('total'),
                func.sum(func.case([(Attendance.status == 'present', 1)], else_=0)).label('present')
            ).join(Attendance).filter(
                and_(
                    ClassSession.teacher_id == current_user_id,
                    ClassSession.date >= start_date,
                    ClassSession.date <= end_date
                )
            ).group_by(ClassSession.date).order_by(ClassSession.date).all()
            
            trend_data = []
            for date, total, present in sessions_data:
                percentage = (present / total * 100) if total > 0 else 0
                trend_data.append({
                    'date': date.isoformat(),
                    'total': total,
                    'present': present,
                    'percentage': round(percentage, 2)
                })
            
            return jsonify({
                'trend_data': trend_data
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/subject-analysis', methods=['GET'])
@jwt_required()
def get_subject_analysis():
    """Get attendance analysis by subject"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.role == 'student':
            # Student subject analysis
            subject_data = db.session.query(
                ClassSession.subject,
                func.count(Attendance.id).label('total'),
                func.sum(func.case([(Attendance.status == 'present', 1)], else_=0)).label('present')
            ).join(Attendance).filter(
                and_(
                    Attendance.user_id == current_user_id,
                    ClassSession.date >= date.today() - timedelta(days=30)
                )
            ).group_by(ClassSession.subject).all()
            
            analysis = []
            for subject, total, present in subject_data:
                percentage = (present / total * 100) if total > 0 else 0
                analysis.append({
                    'subject': subject,
                    'total_sessions': total,
                    'present_sessions': present,
                    'attendance_percentage': round(percentage, 2)
                })
            
            return jsonify({
                'subject_analysis': analysis
            }), 200
        
        elif user.role == 'teacher':
            # Teacher subject analysis
            subject_data = db.session.query(
                ClassSession.subject,
                func.count(Attendance.id).label('total'),
                func.sum(func.case([(Attendance.status == 'present', 1)], else_=0)).label('present')
            ).join(Attendance).filter(
                and_(
                    ClassSession.teacher_id == current_user_id,
                    ClassSession.date >= date.today() - timedelta(days=30)
                )
            ).group_by(ClassSession.subject).all()
            
            analysis = []
            for subject, total, present in subject_data:
                percentage = (present / total * 100) if total > 0 else 0
                analysis.append({
                    'subject': subject,
                    'total_attendances': total,
                    'present_attendances': present,
                    'attendance_percentage': round(percentage, 2)
                })
            
            return jsonify({
                'subject_analysis': analysis
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 