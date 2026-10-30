

"""Joplin note validation functions.

This module provides functions to validate Joplin note additions and deletions
by checking the underlying SQLite database.

Usage:
    from android_world.task_evals.custom_validators import joplin

    # Get notes before and after operation
    before = joplin.get_notes(env)
    # ... perform operation ...
    after = joplin.get_notes(env)

    # Validate note creation
    is_created = joplin.validate_note_created(
        before, after, title="Meeting Notes", body="Discussion points..."
    )

    # Validate note deletion
    is_deleted = joplin.validate_note_deleted(before, after, note_id="abc123")
"""

from typing import Optional

from android_world.env import interface
from android_world.task_evals.custom_validators import llm_as_judge
from android_world.task_evals.utils import sqlite_schema_utils
from android_world.task_evals.utils import sqlite_utils


# Database path for Joplin
_DB_PATH = "/data/data/net.cozic.joplin/databases/joplin.sqlite"
_NOTES_TABLE = "notes"
_FOLDER_TABLE = "folders"
_APP_NAME = "joplin"


JOPLIN_NOTE_PROMPT = """You are a note validation assistant. Please determine whether the actual added note meets the task requirements.

Task Requirements (Expected Note):
- Title: {expected_title}
- Body: {expected_body}

Actual Added Note:
- Title: {actual_title}
- Body: {actual_body}

Judgment Rules:
1. Judge holistically - consider the entire note as a whole, not just individual fields
2. The actual note is considered correct if it conveys the same core information as the expected note
3. Extra content in the actual note body is acceptable IF it is:
   - Repetitions or rephrasings of information already present in the title
   - Natural summaries or expansions that don't add new information
4. Missing content in the actual note is acceptable IF the information is implied by the title
5. Examples of SUCCESS:
   - Expected: Body="Not specified", Actual: Body="Meeting notes for project X" (when title mentions "Project X Meeting") -> SUCCESS (body just repeats title info)
   - Expected: Body="Buy milk", Actual: Body="Remember to buy milk from the store" -> SUCCESS (core info "buy milk" is present)
6. Examples of FAILURE:
   - Expected: Title="Meeting Notes", Actual: Title="Shopping List" -> FAILURE (completely different topic)
   - Expected: Body="Call John at 5pm", Actual: Body="Call Mary at 3pm" -> FAILURE (different person and time)
   - Expected: Body="Project deadline tomorrow", Actual: Body="Not specified" -> FAILURE (missing critical info)
7. Focus on semantic equivalence at the note level, not strict field-by-field matching
"""


def get_folders(env: interface.AsyncEnv) -> list[sqlite_schema_utils.JoplinFolder]:
    """Get all folders (notebooks) from the Joplin database.

    Args:
        env: The Android environment interface.

    Returns:
        A list of JoplinFolder objects.
    """
    return sqlite_utils.get_rows_from_remote_device(
        _FOLDER_TABLE,
        _DB_PATH,
        sqlite_schema_utils.JoplinFolder,
        env,
    )


def get_folder_name_to_id_mapping(env: interface.AsyncEnv) -> dict[str, str]:
    """Get a mapping from folder name to folder ID.

    Args:
        env: The Android environment interface.

    Returns:
        A dictionary mapping folder name (title) to folder ID.
    """
    folders = get_folders(env)
    return {folder.title: folder.id for folder in folders}


def get_id_to_folder_name_mapping(env: interface.AsyncEnv) -> dict[str, str]:
    """Get a mapping from folder ID to folder name.

    Args:
        env: The Android environment interface.

    Returns:
        A dictionary mapping folder ID to folder name (title).
    """
    folders = get_folders(env)
    return {folder.id: folder.title for folder in folders}


def get_notes(env: interface.AsyncEnv) -> list[sqlite_schema_utils.JoplinNote]:
    """Get all notes from the Joplin database.

    Args:
        env: The Android environment interface.

    Returns:
        A list of JoplinNote objects.
    """
    return sqlite_utils.get_rows_from_remote_device(
        _NOTES_TABLE,
        _DB_PATH,
        sqlite_schema_utils.JoplinNote,
        env,
    )


def _normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching.

    Args:
        text: The text to normalize.

    Returns:
        Normalized text (lowercase, stripped).
    """
    return text.lower().strip()


def _note_matches(
    note: sqlite_schema_utils.JoplinNote,
    title: Optional[str] = None,
    body: Optional[str] = None,
    parent_id: Optional[str] = None,
    is_todo: Optional[int] = None,
    fuzzy_match_title: bool = True,
) -> bool:
    """Check if a note matches the given criteria.

    Args:
        note: The note to check.
        title: Expected title.
        body: Expected body content (exact match).
        parent_id: Expected parent folder ID.
        is_todo: Whether it's a todo item.
        fuzzy_match_title: If True, use fuzzy matching for title (ignore case, strip whitespace).

    Returns:
        True if the note matches all provided criteria.
    """
    if title is not None:
        if fuzzy_match_title:
            if _normalize_text(note.title) != _normalize_text(title):
                return False
        else:
            if note.title != title:
                return False
    if body is not None and note.body != body:
        return False
    if parent_id is not None and note.parent_id != parent_id:
        return False
    if is_todo is not None and note.is_todo != is_todo:
        return False
    return True


def validate_note_created(
    before: list[sqlite_schema_utils.JoplinNote],
    after: list[sqlite_schema_utils.JoplinNote],
    title: str,
    body: Optional[str] = None,
    parent_id: Optional[str] = None,
    check_integrity: bool = True,
    fuzzy_match_title: bool = True,
) -> bool:
    """Validate that a specific note has been created.

    Args:
        before: Notes before the operation.
        after: Notes after the operation.
        title: Expected note title.
        body: Expected note body (optional).
        parent_id: Expected parent folder ID (optional).
        check_integrity: If True, also check that existing notes are unchanged.
        fuzzy_match_title: If True, use fuzzy matching for title (ignore case, strip whitespace).

    Returns:
        True if the note was created correctly.
    """
    # Find matching note in 'after'
    matching_after = [
        n for n in after
        if _note_matches(n, title, body, parent_id, fuzzy_match_title=fuzzy_match_title)
    ]

    if not matching_after:
        return False

    # Check that the matching note was not already in 'before'
    for note in matching_after:
        if note not in before:
            if check_integrity:
                # Verify that all original notes are still present
                for old_note in before:
                    if old_note not in after:
                        return False
                # Verify count increased by 1
                if len(after) != len(before) + 1:
                    return False
            return True

    return False


def validate_note_deleted(
    before: list[sqlite_schema_utils.JoplinNote],
    after: list[sqlite_schema_utils.JoplinNote],
    note_id: Optional[str] = None,
    title: Optional[str] = None,
    check_integrity: bool = True,
) -> bool:
    """Validate that a specific note has been deleted.

    Args:
        before: Notes before the operation.
        after: Notes after the operation.
        note_id: ID of the note to delete (preferred).
        title: Note title to match (used if note_id not provided).
        check_integrity: If True, also check that other notes are unchanged.

    Returns:
        True if the note was deleted correctly.
    """
    # Find the note to delete in 'before'
    note_to_delete = None

    if note_id is not None:
        for note in before:
            if note.id == note_id:
                note_to_delete = note
                break
    else:
        for note in before:
            if note.title == title:
                note_to_delete = note
                break

    if note_to_delete is None:
        return False

    # Check that the note is not in 'after'
    if note_to_delete in after:
        return False

    if check_integrity:
        # Verify that all other notes are still present
        for old_note in before:
            if old_note != note_to_delete and old_note not in after:
                return False
        # Verify count decreased by 1
        if len(after) != len(before) - 1:
            return False

    return True





def find_note_by_title(
    notes: list[sqlite_schema_utils.JoplinNote],
    title: str,
    fuzzy_match: bool = True,
) -> Optional[sqlite_schema_utils.JoplinNote]:
    """Find a note by title.

    Args:
        notes: List of notes to search.
        title: Title to search for.
        fuzzy_match: If True, use fuzzy matching (ignore case, strip whitespace).

    Returns:
        The first matching note, or None if not found.
    """
    if fuzzy_match:
        normalized_title = _normalize_text(title)
        for note in notes:
            if _normalize_text(note.title) == normalized_title:
                return note
    else:
        for note in notes:
            if note.title == title:
                return note
    return None


# ============================================================================
# 封装验证函数：接收 env 参数，可被多个任务类复用
# ============================================================================

def validate_note_added(
    env: interface.AsyncEnv,
    goal: str,
    before_notes: list[sqlite_schema_utils.JoplinNote],
    expected_title: str,
    expected_body: Optional[str] = None,
) -> bool:
    """验证单个笔记是否被正确添加，使用 LLM 进行判断。

    Args:
        env: Android 环境接口。
        goal: 任务目标描述。
        before_notes: 任务执行前的笔记列表。
        expected_title: 期望的笔记标题。
        expected_body: 期望的笔记内容（可选）。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_notes = get_notes(env)

    print(f"[DEBUG] Before notes: {len(before_notes)}")
    print(f"[DEBUG] After notes: {len(after_notes)}")
    print(f"[DEBUG] Expected: title='{expected_title}'")

    # 查找新增的笔记
    before_ids = {n.id for n in before_notes}
    new_notes = [n for n in after_notes if n.id not in before_ids]

    print(f"[DEBUG] New notes count: {len(new_notes)}")

    if not new_notes:
        print("[DEBUG] No new notes found, returning False")
        return False

    # 检查是否只添加了一个笔记（验证数量正确性）
    if len(new_notes) != 1:
        print(f"[DEBUG] Expected 1 new note, but found {len(new_notes)}. Validation failed.")
        return False

    # 打印新增笔记详情
    print(f"[DEBUG] ========== New notes ==========")
    for i, note in enumerate(new_notes):
        print(f"[DEBUG] New note {i+1}:")
        print(f"[DEBUG]   title: {note.title}")
        print(f"[DEBUG]   body: {note.body[:100]}..." if note.body else "[DEBUG]   body: (empty)")

    # 取第一个新增笔记进行验证
    actual_note = new_notes[0]

    # 构建 prompt
    prompt = JOPLIN_NOTE_PROMPT.format(
        expected_title=expected_title,
        expected_body=expected_body if expected_body is not None else "Not specified",
        actual_title=actual_note.title if actual_note.title is not None else "Not specified",
        actual_body=actual_note.body if actual_note.body is not None else "Not specified",
    )

    print(f"[DEBUG] Calling LLM to validate note...")
    is_match, explanation = llm_as_judge.llm_judge(goal, prompt)
    print(f"[DEBUG] LLM judgment: {is_match}, Explanation: {explanation}")

    return is_match




def validate_joplin_note_deleted(
    env: interface.AsyncEnv,
    before_notes: list[sqlite_schema_utils.JoplinNote],
    note_title: str,
    notebook: Optional[str] = None,
    check_integrity: bool = True,
    fuzzy_match_title: bool = True,
    fuzzy_match_notebook: bool = True,
) -> bool:
    """验证单个笔记是否被正确删除。

    Args:
        env: Android 环境接口。
        before_notes: 任务执行前的笔记列表。
        note_title: 要删除的笔记标题。
        notebook: 要删除的笔记所在的 notebook（可选，传入则检查，不传入则不检查）。
        check_integrity: 是否检查其他笔记完整性。
        fuzzy_match_title: 是否对标题使用模糊匹配（忽略大小写和空格）。
        fuzzy_match_notebook: 是否对 notebook 名称使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_notes = get_notes(env)

    # 只有当需要检查 notebook 时才获取映射
    id_to_name = None
    if notebook is not None:
        id_to_name = get_id_to_folder_name_mapping(env)

    print(f"[DEBUG] Before notes: {len(before_notes)}")
    print(f"[DEBUG] After notes: {len(after_notes)}")
    print(f"[DEBUG] Looking for note to delete: title='{note_title}'" + (f", notebook='{notebook}'" if notebook else ""))

    # 查找要删除的笔记
    note_to_delete = None
    for note in before_notes:
        # 检查标题
        if fuzzy_match_title:
            if _normalize_text(note.title) != _normalize_text(note_title):
                continue
        else:
            if note.title != note_title:
                continue

        # 检查 notebook（如果指定了）
        if notebook is not None and id_to_name is not None:
            notebook_name = id_to_name.get(note.parent_id, "")
            if fuzzy_match_notebook:
                if _normalize_text(notebook_name) != _normalize_text(notebook):
                    continue
            else:
                if notebook_name != notebook:
                    continue

        note_to_delete = note
        break

    if note_to_delete is None:
        print(f"[DEBUG] No note found with title: {note_title}" + (f" in notebook: {notebook}" if notebook else ""))
        return False

    print(f"[DEBUG] Note to delete: id='{note_to_delete.id}', title='{note_to_delete.title}'")

    result = validate_note_deleted_by_id(
        before_notes,
        after_notes,
        note_id=note_to_delete.id,
        check_integrity=check_integrity,
    )

    print(f"[DEBUG] Note deletion validated: {result}")
    return result


def validate_joplin_notes_deleted(
    env: interface.AsyncEnv,
    before_notes: list[sqlite_schema_utils.JoplinNote],
    note_titles: list[str],
    notebook: Optional[str] = None,
    check_integrity: bool = True,
    fuzzy_match_title: bool = True,
    fuzzy_match_notebook: bool = True,
) -> bool:
    """验证多个笔记是否被正确删除。

    Args:
        env: Android 环境接口。
        before_notes: 任务执行前的笔记列表。
        note_titles: 要删除的笔记标题列表。
        notebook: 要删除的笔记所在的 notebook（可选，传入则检查，不传入则不检查）。
        check_integrity: 是否检查其他笔记完整性。
        fuzzy_match_title: 是否对标题使用模糊匹配（忽略大小写和空格）。
        fuzzy_match_notebook: 是否对 notebook 名称使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_notes = get_notes(env)

    # 只有当需要检查 notebook 时才获取映射
    id_to_name = None
    if notebook is not None:
        id_to_name = get_id_to_folder_name_mapping(env)

    print(f"[DEBUG] Before notes: {len(before_notes)}")
    print(f"[DEBUG] After notes: {len(after_notes)}")
    print(f"[DEBUG] Looking for notes to delete: titles={note_titles}" + (f", notebook='{notebook}'" if notebook else ""))

    # 查找要删除的笔记ID
    note_ids_to_delete = []
    for note in before_notes:
        # 检查标题
        title_matched = False
        if fuzzy_match_title:
            normalized_titles = [_normalize_text(t) for t in note_titles]
            if _normalize_text(note.title) in normalized_titles:
                title_matched = True
        else:
            if note.title in note_titles:
                title_matched = True

        if not title_matched:
            continue

        # 检查 notebook（如果指定了）
        if notebook is not None and id_to_name is not None:
            notebook_name = id_to_name.get(note.parent_id, "")
            if fuzzy_match_notebook:
                if _normalize_text(notebook_name) != _normalize_text(notebook):
                    continue
            else:
                if notebook_name != notebook:
                    continue

        note_ids_to_delete.append(note.id)

    if not note_ids_to_delete:
        print(f"[DEBUG] No notes found with titles: {note_titles}" + (f" in notebook: {notebook}" if notebook else ""))
        return False

    print(f"[DEBUG] Notes to delete: {note_ids_to_delete}")

    result = validate_notes_deleted_by_ids(
        before_notes,
        after_notes,
        note_ids=note_ids_to_delete,
        check_integrity=check_integrity,
    )

    print(f"[DEBUG] Multiple notes deletion validated: {result}")
    return result


def validate_note_deleted_by_id(
    before: list[sqlite_schema_utils.JoplinNote],
    after: list[sqlite_schema_utils.JoplinNote],
    note_id: str,
    check_integrity: bool = True,
) -> bool:
    """Validate that a specific note has been deleted by ID.

    This is an internal function used by validate_note_deleted.

    Args:
        before: Notes before the operation.
        after: Notes after the operation.
        note_id: ID of the note to delete.
        check_integrity: If True, also check that other notes are unchanged.

    Returns:
        True if the note was deleted correctly.
    """
    # Find the note to delete in 'before'
    note_to_delete = None
    for note in before:
        if note.id == note_id:
            note_to_delete = note
            break

    if note_to_delete is None:
        return False

    # Check that the note is not in 'after'
    if note_to_delete in after:
        return False

    if check_integrity:
        # Verify that all other notes are still present
        for old_note in before:
            if old_note != note_to_delete and old_note not in after:
                return False
        # Verify count decreased by 1
        if len(after) != len(before) - 1:
            return False

    return True


def validate_notes_deleted_by_ids(
    before: list[sqlite_schema_utils.JoplinNote],
    after: list[sqlite_schema_utils.JoplinNote],
    note_ids: list[str],
    check_integrity: bool = True,
) -> bool:
    """Validate that multiple notes have been deleted by IDs.

    This is an internal function used by validate_notes_deleted.

    Args:
        before: Notes before the operation.
        after: Notes after the operation.
        note_ids: IDs of notes to delete.
        check_integrity: If True, also check that other notes are unchanged.

    Returns:
        True if all specified notes were deleted correctly.
    """
    # Verify all IDs exist in 'before'
    for note_id in note_ids:
        if not any(n.id == note_id for n in before):
            return False

    # Check that specified notes are not in 'after'
    for note in before:
        if note.id in note_ids:
            if note in after:
                return False

    if check_integrity:
        # Verify that all other notes are still present
        for old_note in before:
            if old_note.id not in note_ids and old_note not in after:
                return False
        # Verify count decreased correctly
        if len(after) != len(before) - len(note_ids):
            return False

    return True