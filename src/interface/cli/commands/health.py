"""
healthcheck 커맨드 — 시스템 상태 점검
"""
import typer
from pathlib import Path
from config import config
from infra.adapters.utils.console_logger import ConsoleLogger

logger = ConsoleLogger(name="healthcheck")


def _check(label: str, ok: bool, hint: str = "") -> bool:
    status = "OK" if ok else "FAIL"
    logger.info(f"  [{status}] {label}")
    if not ok and hint:
        logger.warning(f"       => {hint}")
    return ok


def health_check():
    """
    시스템 헬스 체크

    필수 파일 존재 여부 및 Google Drive 연결 상태를 점검합니다.
    """
    logger.info("=" * 50)
    logger.info("  시스템 헬스 체크")
    logger.info("=" * 50)

    all_ok = True

    # 1. 환경 변수 파일
    logger.info("")
    logger.info("[1] 필수 파일 점검")
    env_file = Path(".env")
    if not _check(".env", env_file.exists(), ".env 파일을 프로젝트 루트에 작성해 주세요."):
        all_ok = False

    # 2. Google 인증 파일
    client_secret = Path(config.GOOGLE_CLIENT_SECRET_FILE)
    if not _check(
        f"Client Secret  ({client_secret})",
        client_secret.exists(),
        f"{config.GOOGLE_CLIENT_SECRET_FILE} 위치에 파일을 넣어 주세요.",
    ):
        all_ok = False

    token_file = Path(config.GOOGLE_TOKEN_FILE)
    token_ok = _check(
        f"Auth Token     ({token_file})",
        token_file.exists(),
        "uv run crawler auth 명령어로 인증을 진행해 주세요.",
    )

    # 3. Parquet 저장소 확인
    logger.info("")
    logger.info("[2] Parquet 저장소 점검")
    parquet_dir = config.OUTPUT_DIR / "parquet"
    if parquet_dir.exists():
        files = list(parquet_dir.glob("*.parquet"))
        _check(
            f"Parquet 저장소  ({parquet_dir})",
            True,
            "",
        )
        logger.info(f"       => {len(files)}개 연도 파일: {[f.stem for f in sorted(files)]}")
    else:
        _check(
            f"Parquet 저장소  ({parquet_dir})",
            False,
            "아직 크롤링 이력 없음. uv run crawler full 을 실행해 주세요.",
        )

    # 4. Google Drive 연결 테스트
    logger.info("")
    logger.info("[3] Google Drive 연결 테스트")
    if token_ok:
        try:
            from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter
            storage = GoogleDriveAdapter()
            files = storage.list_files()
            _check("Google Drive 연결", True)
            logger.info(f"       => 조회된 파일 수: {len(files)}개")
        except Exception as e:
            _check("Google Drive 연결", False, str(e))
            all_ok = False
    else:
        logger.warning("  [SKIP] 토큰 파일이 없어 연결 테스트를 건너뜁니다.")

    # 결과 요약
    logger.info("")
    logger.info("=" * 50)
    if all_ok:
        logger.info("  결과: 모든 항목 정상")
    else:
        logger.error("  결과: 일부 항목 확인 필요 (위 FAIL 항목을 확인하세요)")
        logger.info("=" * 50)
        raise typer.Exit(code=1)
    logger.info("=" * 50)
