import typer
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter

# 커스텀 테마 정의
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
})

console = Console(theme=custom_theme)

def auth_drive():
    """
    구글 드라이브 인증 (토큰 생성용)
    
    크롤링 없이 오직 구글 드라이브 인증만 수행하여 token.json을 생성합니다.
    """
    console.print(Panel.fit("🔐 Google Drive 인증 도구", style="bold blue"))
    
    try:
        # 무거운 의존성 주입(build_dependencies) 대신 필요한 어댑터만 가볍게 초기화
        console.print("[info]Google Drive 어댑터를 초기화합니다...[/info]")
        storage = GoogleDriveAdapter()
        
        # 인증 트리거 (파일 목록 조회 시도)
        console.print("[warning]구글 로그인 창이 열리면 인증을 진행해주세요...[/warning]")
        
        # 실제 인증 및 API 호출 테스트
        files = storage.list_files(query="trashed = false")
        
        console.print(Panel(f"[success]✅ 인증 성공! (token.json 생성됨)[/success]\n\n현재 드라이브 파일 수: {len(files)}개", title="인증 완료", border_style="green"))
        
    except Exception as e:
        console.print(f"[error]❌ 인증 실패:[/error] {e}")
        raise typer.Exit(code=1)
