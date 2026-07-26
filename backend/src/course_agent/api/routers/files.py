"""Course-material upload and retrieval endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ...app_logger import logger
from ...course_material_service import (
    MAX_UPLOAD_BYTES,
    calculate_sha256,
    create_course_file_data,
    create_storage_name,
    delete_course_file_data,
    get_course_file_data,
    get_owned_file_storage_data,
    list_course_files_data,
    replace_document_chunks_data,
    sanitize_original_filename,
    set_course_file_parse_failed_data,
    set_course_file_parsing_data,
    storage_path_for,
)
from ...document_parser import (
    DocumentParseError,
    parse_document,
    validate_file_signature,
)
from ...models import ToolResponse
from ..dependencies import get_current_user
from ..schemas import FileDeleteRequest


router = APIRouter(prefix="/api/v1", tags=["course files"])


async def _save_upload_to_storage(
    uploaded_file: UploadFile,
    destination: Path,
) -> int:
    """Stream an upload to temporary storage while enforcing the size limit."""
    temporary_path = destination.with_name(f".{destination.name}.uploading")
    total_size = 0
    try:
        with temporary_path.open("xb") as target:
            while chunk := await uploaded_file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="单个课程文件不能超过 20 MB。",
                    )
                target.write(chunk)
        if total_size == 0:
            raise HTTPException(status_code=400, detail="不允许上传空文件。")
        temporary_path.replace(destination)
        return total_size
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await uploaded_file.close()


@router.post("/files", status_code=201)
async def upload_course_file_api(
    course_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Persist a user-scoped source file and synchronously parse it locally."""
    user_id = int(current_user["id"])
    original_filename = ""
    final_path: Path | None = None
    metadata_created = False
    try:
        original_filename, file_type = sanitize_original_filename(file.filename)
        storage_filename = create_storage_name(file_type)
        final_path = storage_path_for(user_id, storage_filename)
        file_size = await _save_upload_to_storage(file, final_path)
        validate_file_signature(final_path, file_type)
        course_file = create_course_file_data(
            user_id=user_id,
            course_id=course_id.strip(),
            original_filename=original_filename,
            storage_filename=storage_filename,
            file_type=file_type,
            file_size=file_size,
            file_sha256=calculate_sha256(final_path),
        )
        metadata_created = True
        set_course_file_parsing_data(user_id, course_file.id)
        try:
            parsed_chunks = parse_document(final_path, file_type)
            course_file = replace_document_chunks_data(
                user_id=user_id,
                file_id=course_file.id,
                chunks=parsed_chunks,
            )
        except DocumentParseError as exc:
            course_file = set_course_file_parse_failed_data(
                user_id=user_id,
                file_id=course_file.id,
                error=str(exc),
            )
        except Exception:
            logger.exception("课程文件解析失败：file_id=%s", course_file.id)
            course_file = set_course_file_parse_failed_data(
                user_id=user_id,
                file_id=course_file.id,
                error="文件解析失败，请检查文件是否损坏。",
            )
        return ToolResponse(
            success=True,
            data=course_file.model_dump(mode="json"),
        ).model_dump(mode="json")
    except HTTPException:
        raise
    except ValueError as exc:
        if final_path is not None and not metadata_created:
            final_path.unlink(missing_ok=True)
        return JSONResponse(
            status_code=400,
            content=ToolResponse(success=False, error=str(exc)).model_dump(mode="json"),
        )
    except Exception:
        logger.exception("课程文件上传失败：filename=%r", original_filename)
        if final_path is not None and not metadata_created:
            final_path.unlink(missing_ok=True)
        return JSONResponse(
            status_code=500,
            content=ToolResponse(
                success=False,
                error="课程文件上传失败。",
            ).model_dump(mode="json"),
        )


@router.get("/files")
def list_course_files_api(
    course_id: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        files = list_course_files_data(
            user_id=int(current_user["id"]),
            course_id=course_id,
        )
        return ToolResponse(
            success=True,
            data=[file.model_dump(mode="json") for file in files],
        ).model_dump(mode="json")
    except Exception:
        logger.exception("课程文件列表读取失败")
        return ToolResponse(
            success=False,
            error="课程文件列表读取失败。",
        ).model_dump(mode="json")


@router.get("/files/{file_id}")
def get_course_file_api(
    file_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    course_file = get_course_file_data(int(current_user["id"]), file_id)
    if course_file is None:
        raise HTTPException(status_code=404, detail="没有找到课程文件。")
    return ToolResponse(
        success=True,
        data=course_file.model_dump(mode="json"),
    ).model_dump(mode="json")


@router.delete("/files/{file_id}")
def delete_course_file_api(
    file_id: str,
    request: FileDeleteRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    normalized_file_id = file_id.strip()
    expected_confirmation = f"确认删除文件 {normalized_file_id}"
    if request.confirmation != expected_confirmation:
        raise HTTPException(
            status_code=400,
            detail=f"删除操作未确认，请准确输入：{expected_confirmation}",
        )
    user_id = int(current_user["id"])
    owned_file = get_owned_file_storage_data(user_id, normalized_file_id)
    if owned_file is None:
        raise HTTPException(status_code=404, detail="没有找到课程文件。")
    course_file, storage_filename = owned_file
    storage_path = storage_path_for(user_id, storage_filename)
    try:
        storage_path.unlink(missing_ok=True)
        deleted_file = delete_course_file_data(user_id, normalized_file_id)
    except Exception as exc:
        logger.exception("课程文件删除失败：file_id=%s", normalized_file_id)
        raise HTTPException(status_code=500, detail="课程文件删除失败。") from exc
    return ToolResponse(
        success=True,
        data={
            "deleted_file": deleted_file.model_dump(mode="json"),
            "message": "课程文件已删除。",
        },
    ).model_dump(mode="json")
