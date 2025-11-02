from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
import logging
from .models import User, GuestLead
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    PrivateProfileSerializer,
    UserProfileUpdateSerializer,
    GuestLeadSerializer
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        return Response({
            'message': 'User created successfully',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(access_token),
            }
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login user and return JWT tokens
    """
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(access_token),
            }
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET', 'PATCH'])
def profile(request):
    """
    Get or update current user profile (requires authentication)
    """
    if request.method == 'GET':
        serializer = PrivateProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            user = serializer.save()
            # Return updated profile data using PrivateProfileSerializer
            response_serializer = PrivateProfileSerializer(user, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def logout(request):
    """
    Logout user by blacklisting refresh token
    """
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Invalid token'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_guest_lead(request):
    """
    Create a guest lead from onboarding flow.
    Captures email signup and associates with session data.
    """
    # Ensure session exists
    if not request.session.session_key:
        request.session.create()

    # Prepare data with session information
    data = request.data.copy()
    data['session_key'] = request.session.session_key

    # Try to get onboarding flow state from session
    onboarding_flow = request.session.get('onboarding_flow', {})
    if onboarding_flow:
        data['flow_id'] = onboarding_flow.get('flow_id', 'user-onboarding-v1')
        data['guest_attempt_ids'] = onboarding_flow.get('attempt_ids', {})
    else:
        # Fallback to defaults if no flow state
        data.setdefault('flow_id', 'user-onboarding-v1')
        data.setdefault('guest_attempt_ids', {})

    serializer = GuestLeadSerializer(data=data)
    if serializer.is_valid():
        guest_lead = serializer.save()

        logger.info(f"Created guest lead: {guest_lead.email} (session: {request.session.session_key})")

        return Response({
            'message': 'Successfully signed up for updates!',
            'email': guest_lead.email,
            'subscribed_to_updates': guest_lead.subscribed_to_updates
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
