from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from nlp_engine.services import generate_response


@login_required(login_url='/users/login/')
def chatbot_ui(request):
    """
    Render the chatbot UI page
    """
    return render(request, "chatbot.html")


@login_required(login_url='/users/login/')
def ask_question(request):
    """
    Handle chatbot questions and return ML-generated reply
    """
    question = request.GET.get("q", "").strip()

    if not question:
        return JsonResponse({"reply": "Please ask a question."})

    reply = generate_response(question)

    return JsonResponse({"reply": reply})
