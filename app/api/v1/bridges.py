"""
Puentes de Email (Bridges)

Estos endpoints actúan como intermediarios entre los emails de Supabase y la app.
- Reciben redirecciones de Supabase después de verificar OTP
- Devuelven HTML con deep links a la app
- NO requieren parámetros obligatorios (Supabase maneja la verificación)
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
import logging
from uuid import UUID

from app.db.supabase import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")


@router.get(
    "/confirm",
    summary="Puente: Confirmar email desde enlace",
)
async def confirm_email(
    code: str = Query(None),
    token: str = Query(None),
    email: str = Query(None),
    type: str = Query(None),
):
    """
    🌉 PUENTE: Endpoint que recibe la redirección de Supabase tras verificar OTP.

    FLUJO:
    1. Usuario se registra en la app
    2. Supabase envía email con link:
       https://pqsohqwhrzwuhdqlilqf.supabase.co/auth/v1/verify?token=XXX&type=signup&redirect_to=https://api.misboletas.tech/api/v1/auth/confirm
    3. Usuario hace click → Supabase verifica el token
    4. Supabase redirige a THIS endpoint con ?code= o ?token=
    5. Este endpoint obtiene la sesión y abre la app

    VENTAJAS:
    - Supabase ya verificó el OTP, es seguro
    - El usuario ve HTML amigable en el navegador
    - JavaScript abre el deep link a la app
    - Funciona en todos los dispositivos
    """
    try:
        logger.info(
            f"[🌉 PUENTE] Confirm endpoint llamado: code={code}, token={token}, email={email}, type={type}"
        )

        # Supabase verifica el token EN SU SERVIDOR y luego redirige aquí
        # La sesión del usuario ya está verificada
        # Intentar obtener la sesión actual de Supabase
        try:
            session = supabase.client.auth.get_session()
            if session and session.user and session.session:
                logger.info(
                    f"[✅ PUENTE] Sesión activa encontrada para usuario: {session.user.id}"
                )
                user_id = session.user.id
                user_email = session.user.email or email
                access_token = session.session.access_token
                refresh_token = session.session.refresh_token
            else:
                logger.warning(
                    "[⚠️ PUENTE] No hay sesión activa en cookies, intentando leer desde hash"
                )
                # Supabase puede pasar los datos en el fragmento de la URL (#)
                # Retornar HTML que lea el hash con JavaScript
                html_con_hash = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Email Confirmado</title>
                    <style>
                        body {{ 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                            margin: 0; 
                            padding: 20px; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            min-height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        }}
                        .container {{ 
                            max-width: 500px; 
                            background: white; 
                            padding: 40px; 
                            border-radius: 12px; 
                            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                            text-align: center;
                        }}
                        .icon {{ font-size: 60px; margin: 0 0 20px 0; }}
                        h1 {{ 
                            color: #333; 
                            font-size: 24px; 
                            margin: 0 0 15px 0;
                            font-weight: 600;
                        }}
                        p {{ 
                            color: #666; 
                            font-size: 15px;
                            line-height: 1.6;
                            margin: 0 0 30px 0;
                        }}
                        .button {{
                            display: inline-block;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            padding: 14px 40px;
                            border-radius: 8px;
                            text-decoration: none;
                            font-weight: 600;
                            font-size: 16px;
                            border: none;
                            cursor: pointer;
                            transition: transform 0.2s, box-shadow 0.2s;
                        }}
                        .button:hover {{
                            transform: translateY(-2px);
                            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
                        }}
                        .button:active {{
                            transform: translateY(0);
                        }}
                        .error {{
                            display: none;
                            background-color: #f8d7da;
                            border-left: 4px solid #dc3545;
                            padding: 12px 15px;
                            margin-top: 20px;
                            border-radius: 4px;
                            font-size: 13px;
                            color: #721c24;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">✅</div>
                        <h1>¡Email Confirmado!</h1>
                        <p>Tu cuenta ha sido verificada exitosamente. Ahora puedes iniciar sesión en la app.</p>
                        <button class="button" onclick="openApp()" id="btn-open">📱 Volver a la App</button>
                        <div id="error" class="error"></div>
                    </div>

                    <script>
                        // Leer el fragmento de la URL que Supabase envía
                        const hash = window.location.hash;
                        console.log('Hash recibido:', hash);
                        
                        // Parsear los parámetros del hash
                        const params = new URLSearchParams(hash.substring(1));
                        const accessToken = params.get('access_token');
                        const refreshToken = params.get('refresh_token');
                        const userId = params.get('user_id');
                        
                        // Variable global para el deep link
                        let deepLink = null;
                        
                        if (accessToken && refreshToken) {{
                            console.log('✅ Tokens encontrados en hash');
                            // Construir deep link con los tokens
                            deepLink = `{settings.DEEP_LINK_BASE}/auth-callback?access_token=${{accessToken}}&refresh_token=${{refreshToken}}&user_id=${{userId || ''}}&type=signup`;
                        }} else {{
                            console.log('⚠️ No se encontraron tokens en hash');
                            // Fallback: abrir la app sin tokens (la app manejará el login)
                            deepLink = '{settings.DEEP_LINK_BASE}/auth-callback';
                        }}
                        
                        // Solo ejecutar cuando el usuario haga click
                        function openApp() {{
                            if (deepLink) {{
                                window.location.href = deepLink;
                                // Si después de 3 segundos no se abrió, mostrar error
                                setTimeout(() => {{
                                    document.getElementById('btn-open').style.display = 'none';
                                    document.getElementById('error').style.display = 'block';
                                    document.getElementById('error').textContent = '❌ No se pudo abrir la app. Asegúrate de tenerla instalada.';
                                }}, 3000);
                            }}
                        }}
                    </script>
                </body>
                </html>
                """
                return HTMLResponse(content=html_con_hash, status_code=200)
        except Exception as e:
            logger.error(f"[ERROR] No se pudo obtener sesión de Supabase: {e}")
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 8px; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>❌ Error al Confirmar</h1>
                    <p>Por favor, intenta más tarde o contacta a soporte.</p>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=500)

        # ✅ CONSTRUIR DEEP LINK CON TOKENS VERIFICADOS
        # Usar DEEP_LINK_BASE desde configuración (variable de entorno)
        deep_link = f"{settings.DEEP_LINK_BASE}/auth-callback?access_token={access_token}&refresh_token={refresh_token}&user_id={user_id}&type={type or 'signup'}&email={user_email}"
        logger.info(
            f"[🌐 PUENTE] Deep link construido: {settings.DEEP_LINK_BASE}/auth-callback con tokens"
        )

        # HTML BONITO CON SPINNER Y BOTÓN DE FALLBACK
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>¡Bienvenido a MisBoletas!</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 40px 20px;
                    text-align: center;
                    color: white;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                    text-align: center;
                }}
                .content h2 {{
                    color: #333333;
                    font-size: 20px;
                    margin: 0 0 15px 0;
                }}
                .content p {{
                    color: #666666;
                    font-size: 14px;
                    line-height: 1.6;
                    margin: 10px 0;
                }}
                .spinner {{
                    display: inline-block;
                    width: 40px;
                    height: 40px;
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #667eea;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 20px 0;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                .button {{
                    display: inline-block;
                    background-color: #667eea;
                    color: white;
                    padding: 16px 40px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 25px 0;
                    border: 2px solid #667eea;
                    cursor: pointer;
                }}
                .button:hover {{
                    background-color: #764ba2;
                    border-color: #764ba2;
                }}
                .footer {{
                    background-color: #f9f9f9;
                    padding: 20px 30px;
                    text-align: center;
                    border-top: 1px solid #eeeeee;
                }}
                .footer p {{
                    color: #999999;
                    font-size: 12px;
                    margin: 5px 0;
                }}
                .footer a {{
                    color: #667eea;
                    text-decoration: none;
                }}
                .error {{
                    display: none;
                    background-color: #f8d7da;
                    border-left: 4px solid #dc3545;
                    padding: 12px 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                    font-size: 13px;
                    color: #721c24;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>¡Bienvenido a MisBoletas!</h1>
                </div>
                
                <div class="content">
                    <h2>✅ ¡Email Confirmado!</h2>
                    
                    <p>Tu correo ha sido verificado exitosamente.</p>
                    
                    <button class="button" onclick="openApp()" id="btn-open">📱 Volver a la App</button>
                    
                    <div id="error" class="error"></div>
                </div>
                
                <div class="footer">
                    <p>© 2025 MisBoletas. Todos los derechos reservados.</p>
                    <p><a href="https://misboletas.tech">Visita nuestro sitio web</a></p>
                </div>
            </div>

            <script>
                const deepLink = '{deep_link}';

                function openApp() {{
                    if (deepLink) {{
                        window.location.href = deepLink;
                        // Si después de 3 segundos no se abrió, mostrar error
                        setTimeout(() => {{
                            document.getElementById('btn-open').style.display = 'none';
                            document.getElementById('error').style.display = 'block';
                            document.getElementById('error').textContent = '❌ No se pudo abrir la app. Asegúrate de tenerla instalada.';
                        }}, 3000);
                    }}
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=success_html, status_code=200)

    except Exception as e:
        logger.error(f"[ERROR] Confirm bridge failed: {str(e)}")
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Error</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                h1 {{ color: #d32f2f; }}
                p {{ color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⏰ Error Procesando Confirmación</h1>
                <p>Por favor, intenta nuevamente o contacta a soporte.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)


@router.get(
    "/reset-password",
    summary="Puente: Restablecer contraseña",
)
async def reset_password_bridge(
    code: str = Query(None),
    token: str = Query(None),
    email: str = Query(None),
    type: str = Query(None),
):
    """
    🌉 PUENTE: Endpoint para recuperación de contraseña.

    Similar a /confirm pero para el flujo de reset password.
    """
    try:
        logger.info(f"[🌉 PUENTE] Reset password bridge - email={email}, type={type}")

        # Obtener sesión de Supabase (después de verificar recovery token)
        try:
            session = supabase.client.auth.get_session()
            if session and session.user and session.session:
                logger.info(f"[✅ PUENTE] Sesión recovery encontrada")
                access_token = session.session.access_token
                user_email = session.user.email or email

                # Para reset password, usar el access_token como token
                deep_link = f"misboletas://reset-password?token={access_token}&email={user_email}"
            else:
                # Si no hay sesión, algo salió mal
                error_html = """
                <html>
                <body style="text-align: center; padding: 50px; font-family: Arial;">
                    <h1>❌ Error de Verificación</h1>
                    <p>No se pudo verificar tu identidad. Por favor, intenta solicitando un nuevo enlace.</p>
                </body>
                </html>
                """
                return HTMLResponse(content=error_html, status_code=400)
        except Exception as e:
            logger.error(f"[ERROR] Reset password session failed: {e}")
            error_html = """
            <html>
            <body style="text-align: center; padding: 50px; font-family: Arial;">
                <h1>❌ Error</h1>
                <p>Por favor, intenta más tarde.</p>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=500)

        # HTML para redirigir a reset password
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Restablecer Contraseña</title>
        </head>
        <body style="text-align: center; padding: 50px; font-family: Arial;">
            <h2>Redirigiendo...</h2>
            <script>
                window.location.href = '{deep_link}';
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=200)

    except Exception as e:
        logger.error(f"[ERROR] Reset password bridge failed: {str(e)}")
        return HTMLResponse(
            content="<html><body><h1>Error</h1></body></html>",
            status_code=500,
        )
