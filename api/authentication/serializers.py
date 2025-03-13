from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from core.models import Parent, Mentor, AgeGroup, UserPreference

User = get_user_model()

class AgeGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeGroup
        fields = ['id', 'name', 'min_age', 'max_age', 'description']

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['color_theme', 'avatar_choice', 'sound_enabled', 'ui_preferences']

class UserSerializer(serializers.ModelSerializer):
    age_group = AgeGroupSerializer(read_only=True)
    age_group_id = serializers.IntegerField(write_only=True, required=False)
    preferences = UserPreferenceSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'display_name', 'date_of_birth', 
                 'age_group', 'age_group_id', 'is_active', 'date_joined', 
                 'last_login', 'preferences']
        read_only_fields = ['id', 'date_joined', 'last_login', 'is_active']

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    age_group_id = serializers.IntegerField(required=True)
    date_of_birth = serializers.DateField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'email', 'display_name', 
                 'date_of_birth', 'age_group_id']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Validate age group exists
        try:
            AgeGroup.objects.get(id=attrs['age_group_id'])
        except AgeGroup.DoesNotExist:
            raise serializers.ValidationError({"age_group_id": "Age group does not exist."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            display_name=validated_data.get('display_name', validated_data['username']),
            date_of_birth=validated_data['date_of_birth'],
            age_group_id=validated_data['age_group_id']
        )
        
        # Create user preferences with defaults
        UserPreference.objects.create(user=user)
        
        return user

class ParentRegistrationSerializer(serializers.ModelSerializer):
    user = RegisterSerializer()
    
    class Meta:
        model = Parent
        fields = ['user', 'name']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = RegisterSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        parent = Parent.objects.create(user=user, **validated_data)
        return parent

class MentorRegistrationSerializer(serializers.ModelSerializer):
    user = RegisterSerializer()
    
    class Meta:
        model = Mentor
        fields = ['user', 'expertise', 'bio']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = RegisterSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        mentor = Mentor.objects.create(user=user, **validated_data)
        return mentor

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs