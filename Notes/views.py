from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import viewsets
from .serializers import NotesSerializer, LabelSerializer, CollaboratorSerializer
from .models import Notes, Label, Collaborator
from user.models import User
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .utils import RedisClient
import json
from django.db.models import Q

# Create your views here.
class NotesAPI(APIView):

    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            cache_notes = RedisClient.get(f'user_{request.user.id}')
            if cache_notes:
                cache_notes_dict = [json.loads(x) for x in cache_notes.values()]  # Parse JSON string to dictionary
                return Response({'message': 'Successfully Fetched Data from Cache', 'status': 200, 'data': cache_notes_dict}, status=200)
            # If cache_notes is empty or None, proceed with fetching data from database
            lookup = Q(user_id=request.user.id) | Q(collaborators__id=request.user.id)
            notes = Notes.objects.filter(lookup)
            serializer = NotesSerializer(notes, many=True)
            return Response({'message': 'Successfully Fetched Data', 'status': 200, 'data': serializer.data}, status=200)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)

    def post(self,request):
        try:
            request.data['user'] = request.user.id
            serializer = NotesSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            note_id = serializer.instance.id
            RedisClient.save(f'user_{request.user.id}', f'note_{note_id}', serializer.data)
            return Response({'message': 'Note Created', 'status': 201, 
                            'data': serializer.data}, status=201)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)
     
    def put(self, request):
        try:
            request.data['user'] = request.user.id
            note_id = request.data.get('id')
            note = Notes.objects.get(id = note_id, user_id=request.data.get('user'))
            serializer = NotesSerializer(instance = note, data = request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            data_json = serializer.data
            RedisClient.save(f'user_{request.user.id}',f'note_{note_id}', data_json)
            return Response({'message': 'Data Updated', 'status': 200, 'data': serializer.data}, status=200)
        except Notes.DoesNotExist:
            return Response({'message': 'Note not found', 'status': 404}, status=404)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)
            
    def delete(self, request):
        try:
            note_id = request.query_params.get('id')
            note = Notes.objects.get(id = note_id)
            user_id = request.user.id
            RedisClient.delete(f'user_{user_id}', f'note_{note_id}')
            note.delete()
            return Response({'message': 'Note Deleted', 'status': 200}, status=200)
        except Notes.DoesNotExist:
            return Response({'msg': 'Notes not found', 'status': 404}, status=404)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)

class ArchiveTrashAPI(viewsets.ViewSet):
        
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def update_archive(self, request):
        try:
            note_id = request.query_params.get('note_id')
            if not note_id:
                return Response({"msg": "Note ID not found", "status": 404}, status=404)
            note = Notes.objects.get(id=note_id, user=request.user)
            note.is_archive = True if not note.is_archive else False
            note.save()
            if note.is_archive:
                return Response({'message': 'Note moved to Archive', 'status':200}, status=200)
            return Response({'message': 'Note moved out of Archive', 'status': 200}, status=200)
        except Notes.DoesNotExist:
            return Response({'message': 'Note does not Exist', 'status': 404}, status=404)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)
        
    def get_archived_notes(self, request):
        try:
            notes = Notes.objects.filter(user=request.user, is_archive=True, is_trash=False)
            serializer = NotesSerializer(notes, many=True)
            return Response({'message': 'Archived Notes', 'status': 200, 'Data': serializer.data}, status=200)
        except Notes.DoesNotExist:
            return Response({'message': 'Note does not Exist', 'status': 404}, status=404)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)

    def update_trash(self, request):
        try:
            note_id = request.query_params.get('note_id')
            if not note_id:
                return Response({"msg": "Note ID not found", "status": 404}, status=404)
            note = Notes.objects.get(id=note_id, user=request.user)
            note.is_trash = True if not note.is_trash else False
            note.save()
            if note.is_trash:
                return Response({'message': 'Note moved to Trash', 'status':200}, status=200)
            return Response({'message': 'Note moved out of Trash', 'status': 200}, status=200)
        except Notes.DoesNotExist:
            return Response({'message': 'Note does not Exist', 'status': 404}, status=404)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)
        
    def get_trash_notes(self, request):
        try:
            notes = Notes.objects.filter(user=request.user, is_trash=True)
            serializer = NotesSerializer(notes, many=True)
            return Response({'message': 'Trashed Notes', 'status': 200, 'Data': serializer.data}, status=200)
        except Notes.DoesNotExist:
            return Response({'message': 'Note does not Exist', 'status': 404}, status=404)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)

class GetOneApi(APIView):

    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def get(self, request):
        try:
            user_id = request.user.id
            note_id = request.query_params.get('id')
            cache_notes = RedisClient.get_one(f'user_{user_id}', f'note_{note_id}')
            if cache_notes:
                cache_notes_dict = json.loads(cache_notes)
                return Response({'message': 'Successfully Fetched Data from cache', 'status': 200, 'data': cache_notes_dict}, status=200)
            note = Notes.objects.get(id = note_id, user_id = user_id)
            serializer = NotesSerializer(note, many=False)
            return Response({'message': 'Successfully Fetched Data', 'status': 200, 'data': serializer.data}, status=200)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)

class LabelAPI(viewsets.ViewSet):
    
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            labels = Label.objects.filter(user_id = request.user.id)
            serializer = LabelSerializer(labels, many=True)
            return Response({'message': 'Successfully Fetched Data', 'status': 200,
                             'data': serializer.data}, status=200)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status = 400)

    def post(self, request):
        try:
            request.data['user'] = request.user.id
            serializer = LabelSerializer(data = request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({'message': 'Label Created Successfully!', 'status': 201, 
                             'data': serializer.data}, status = 201)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status = 400)
        
    def put(self, request):
        try:
            request.data['user'] = request.user.id
            label = Label.objects.get(id = request.data.get('id'), user_id=request.data.get('user'))
            serializer = LabelSerializer(instance = label, data = request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({'message': 'Data Updated', 'status': 200, 'data': serializer.data}, status=200)
        except Label.DoesNotExist:
            return Response({'message': 'Label not found', 'status': 404}, status=404)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)
            
    def delete(self, request):
        try:
            label = Label.objects.get(id = request.data.get('id'))
            label.delete()
            return Response({'message': 'Label Deleted', 'status': 200}, status=200)
        except Notes.DoesNotExist:
            return Response({'msg': 'Label not found', 'status': 404}, status=404)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)            
            
class CollaboratorApi(APIView):
    
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request):
        try:    
            if not request.data["collaborator"]:
                return Response({'message': 'Collaborator ID is not provided.', 'status': 400}, status=400)
            serializer = CollaboratorSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save() 
            return Response({'message': f'Note Shared to user {request.data["collaborator"]}.', 'status': 200}, status=200)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)
        
    def delete(self, request):
        try:
            note = Notes.objects.get(id=request.data['note'], user_id=request.user.id)
            [note.collaborators.remove(user) for user in request.data['collaborator']]
            return Response({'message': f'Access to user {request.data["collaborator"]} removed.', 'status': 200}, status=200)
        except Exception as e:
            return Response({'message': str(e), 'status': 400}, status=400)
            
