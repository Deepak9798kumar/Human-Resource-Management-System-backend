from rest_framework import serializers
from .models import Employee, Attendance
from datetime import date


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['employee_id', 'full_name', 'email', 'department', 'created_at']
        read_only_fields = ['created_at']

    def validate_employee_id(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Employee ID cannot be empty")
        return value.strip()

    def validate_full_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Full name cannot be empty")
        return value.strip()

    def validate_department(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Department cannot be empty")
        return value.strip()


class AttendanceSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField()
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_department = serializers.CharField(source='employee.department', read_only=True)

    class Meta:
        model = Attendance
        fields = ['id', 'employee_id', 'date', 'status', 'created_at', 'employee_name', 'employee_department']
        read_only_fields = ['id', 'created_at', 'employee_name', 'employee_department']

    def validate_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Cannot mark attendance for future dates")
        return value

    def validate_employee_id(self, value):
        try:
            Employee.objects.get(employee_id=value)
        except Employee.DoesNotExist:
            raise serializers.ValidationError(f"Employee with ID '{value}' not found")
        return value

    def create(self, validated_data):
        employee_id = validated_data.pop('employee_id')
        employee = Employee.objects.get(employee_id=employee_id)
        
        # Update or create attendance record
        attendance, created = Attendance.objects.update_or_create(
            employee=employee,
            date=validated_data['date'],
            defaults={'status': validated_data['status']}
        )
        return attendance


class DashboardStatsSerializer(serializers.Serializer):
    total_employees = serializers.IntegerField()
    total_attendance_records = serializers.IntegerField()
    present_today = serializers.IntegerField()
    absent_today = serializers.IntegerField()
