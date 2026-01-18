from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.db import IntegrityError
from .models import Stock
from .forms import StockForm
from django.utils.html import format_html
from django.contrib.auth.decorators import login_required # añadir encima de la funcion def para proteger el contenido de usuarios no autenticados
# pagina de inicio
def home(request):
    return render(request, 'index.html')
# vista para registrar usuarios
def signup(request):
    if request.method == 'GET':
        return render(request, 'signup.html',{
        'form': UserCreationForm()
         })
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(
                username=request.POST['username'],
                password=request.POST['password1'])
                user.save()
                login(request, user) #registro coockie session
                return redirect('login')
            except IntegrityError:
                return render(request, 'signup.html',{
                'form': UserCreationForm(),
                'error':('El usuario ya existe')
                })
                
        return render(request, 'signup.html',{
            'form': UserCreationForm(),
            'error':('Las contraseñas no coinciden')
            })
# vista para iniciar sesion
def signin(request):
    if request.method == 'GET':
        return render(request, 'login.html',{
        'form': AuthenticationForm()
         })
    else:
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user is None:
            return render(request, 'login.html',{
            'form': AuthenticationForm(),
            'error':('El usuario o la contraseña son incorrectos')
            })
        else:
            login(request, user) #crear coockie session
            return redirect('home')
# vista para cerrar sesion
@login_required
def signout(request):
    logout(request)
    return redirect('home')

# vista para la pagina de stock
@login_required

def stock_view(request):
    stocks = Stock.objects.all()
    return render(request, 'stock.html', {'stocks': stocks})

def addstock(request):
    if request.method == 'POST':
        form = StockForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.Usario = request.user  # tu campo se llama así
            vehicle.save()
            return redirect('stock')
    else:
        form = StockForm()

    return render(request, 'add_stock.html', {'form': form})


# vista para la pagina de un item
def item_page(request, stock_id):
    stock = get_object_or_404(Stock, pk=stock_id)
    return render(request, 'item_page.html', {'stock': stock})

#comprabacion de imagenes
def imagen_tag(self):
    if self.imagen:
        return format_html('<img src="{}" width="100" height="100" />', self.imagen.url)
    else:
        return "No Image"