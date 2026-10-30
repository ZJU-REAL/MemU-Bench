

"""封装验证函数：检查 Files 文件管理器操作是否成功。

Files app 是 Android 系统自带的文件管理器应用。
支持的操作包括：创建文件、删除文件、移动文件、创建文件夹、删除文件夹等。
"""

import dataclasses
from typing import Optional
from android_world.env import interface
from android_world.env import adb_utils
from android_world.task_evals.utils import sqlite_schema_utils
from android_world.task_evals.utils import sqlite_utils
from android_world.utils import file_utils
from android_world.utils import fuzzy_match_lib


# Simple Gallery Pro 数据库路径和收藏表名
_GALLERY_DB_PATH = '/data/data/com.simplemobiletools.gallery.pro/databases/gallery.db'
_GALLERY_FAVORITES_TABLE = 'favorites'
_GALLERY_APP_NAME = 'simple gallery pro'


# 默认工作目录
_DEFAULT_BASE_PATH = "/storage/emulated/0"


@dataclasses.dataclass
class FileInfo:
    """文件信息数据结构。

    Attributes:
        name: 文件名。
        path: 文件完整路径。
        is_directory: 是否是目录。
        size: 文件大小（字节）。
    """
    name: str
    path: str
    is_directory: bool = False
    size: int = 0


def get_files_in_directory(
    env: interface.AsyncEnv,
    directory_path: str,
) -> list[FileInfo]:
    """获取目录中的所有文件和文件夹。

    Args:
        env: Android 环境接口。
        directory_path: 目录路径。

    Returns:
        FileInfo 对象列表。
    """
    if not file_utils.check_directory_exists(directory_path, env.controller):
        print(f"[DEBUG] Directory does not exist: {directory_path}")
        return []

    files_with_metadata = file_utils.get_file_list_with_metadata(
        directory_path, env.controller
    )

    files = []
    for f in files_with_metadata:
        files.append(FileInfo(
            name=f.file_name,
            path=f.full_path,
            is_directory=False,
            size=f.file_size,
        ))

    print(f"[DEBUG] Found {len(files)} files in {directory_path}")
    return files


def get_all_files_recursive(
    env: interface.AsyncEnv,
    directory_path: str,
) -> list[FileInfo]:
    """递归获取目录中的所有文件。

    Args:
        env: Android 环境接口。
        directory_path: 目录路径。

    Returns:
        FileInfo 对象列表。
    """
    if not file_utils.check_directory_exists(directory_path, env.controller):
        print(f"[DEBUG] Directory does not exist: {directory_path}")
        return []

    all_files = []

    # 获取当前目录的文件
    files = get_files_in_directory(env, directory_path)
    all_files.extend(files)

    # 递归获取子目录的文件
    from android_world.env import adb_utils
    res = adb_utils.issue_generic_request(
        ["shell", "find", directory_path, "-type", "d"],
        env.controller,
    )
    if res.status:
        subdirs = res.generic.output.decode().replace("\r", "").strip().split("\n")
        for subdir in subdirs[1:]:  # 跳过根目录本身
            if subdir:
                files = get_files_in_directory(env, subdir)
                all_files.extend(files)

    print(f"[DEBUG] Found {len(all_files)} files recursively in {directory_path}")
    return all_files


def create_file(
    env: interface.AsyncEnv,
    file_name: str,
    directory_path: str,
    content: str = "",
) -> str:
    """创建一个文件。

    Args:
        env: Android 环境接口。
        file_name: 文件名。
        directory_path: 目录路径。
        content: 文件内容。

    Returns:
        创建的文件内容。
    """
    content = file_utils.create_file(
        file_name, directory_path, env.controller, content
    )
    print(f"[DEBUG] Created file: {file_name} in {directory_path}")
    return content


def delete_file(
    env: interface.AsyncEnv,
    file_name: str,
    directory_path: str,
) -> bool:
    """删除一个文件。

    Args:
        env: Android 环境接口。
        file_name: 文件名。
        directory_path: 目录路径。

    Returns:
        是否删除成功。
    """
    file_utils.remove_single_file(file_name, directory_path, env.controller)
    print(f"[DEBUG] Deleted file: {file_name} from {directory_path}")
    return True


def create_directory(
    env: interface.AsyncEnv,
    directory_name: str,
    parent_path: str,
) -> bool:
    """创建一个目录。

    Args:
        env: Android 环境接口。
        directory_name: 目录名。
        parent_path: 父目录路径。

    Returns:
        是否创建成功。
    """
    new_path = file_utils.convert_to_posix_path(parent_path, directory_name)
    file_utils.mkdir(new_path, env.controller)
    print(f"[DEBUG] Created directory: {new_path}")
    return True


def clear_directory(
    env: interface.AsyncEnv,
    directory_path: str,
) -> None:
    """清空目录中的所有内容。

    Args:
        env: Android 环境接口。
        directory_path: 目录路径。
    """
    file_utils.clear_directory(directory_path, env.controller)
    print(f"[DEBUG] Cleared directory: {directory_path}")


def file_exists(
    env: interface.AsyncEnv,
    file_name: str,
    directory_path: str,
) -> bool:
    """检查文件是否存在。

    Args:
        env: Android 环境接口。
        file_name: 文件名。
        directory_path: 目录路径。

    Returns:
        文件是否存在。
    """
    return file_utils.check_file_or_folder_exists(
        file_name, directory_path, env.controller
    )


def directory_exists(
    env: interface.AsyncEnv,
    directory_path: str,
) -> bool:
    """检查目录是否存在。

    Args:
        env: Android 环境接口。
        directory_path: 目录路径。

    Returns:
        目录是否存在。
    """
    return file_utils.check_directory_exists(directory_path, env.controller)


def get_file_content(
    env: interface.AsyncEnv,
    file_path: str,
) -> str:
    """获取文件内容。

    Args:
        env: Android 环境接口。
        file_path: 文件完整路径。

    Returns:
        文件内容。
    """
    from android_world.env import adb_utils
    res = adb_utils.issue_generic_request(
        ["shell", "cat", file_path],
        env.controller,
    )
    content = res.generic.output.decode().replace("\r", "")
    return content


def validate_file_created(
    env: interface.AsyncEnv,
    file_name: str,
    directory_path: str,
    expected_content: Optional[str] = None,
    fuzzy_match: bool = True,
) -> bool:
    """验证文件是否被正确创建。

    Args:
        env: Android 环境接口。
        file_name: 文件名。
        directory_path: 目录路径。
        expected_content: 期望的文件内容（可选）。
        fuzzy_match: 是否对内容使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    print(f"[DEBUG] Checking if file exists: {file_name} in {directory_path}")

    if not file_exists(env, file_name, directory_path):
        print(f"[DEBUG] File does not exist: {file_name}")
        return False

    print(f"[DEBUG] File exists: {file_name}")

    # 如果指定了内容，检查内容
    if expected_content is not None:
        file_path = file_utils.convert_to_posix_path(directory_path, file_name)
        content = get_file_content(env, file_path)
        print(f"[DEBUG] File content: '{content[:100]}...' (truncated)")
        print(f"[DEBUG] Expected content: '{expected_content[:100]}...' (truncated)")

        if fuzzy_match:
            if not fuzzy_match_lib.fuzzy_match(content.strip(), expected_content.strip()):
                print(f"[DEBUG] Content does not match (fuzzy)")
                return False
        else:
            if content.strip() != expected_content.strip():
                print(f"[DEBUG] Content does not match (exact)")
                return False

    print(f"[DEBUG] File creation validated: True")
    return True


def validate_file_deleted(
    env: interface.AsyncEnv,
    file_name: str,
    directory_path: str,
    initial_files: Optional[list[str]] = None,
) -> bool:
    """验证文件是否被正确删除。

    如果提供了 initial_files，还会检查是否只有目标文件被删除，
    其他文件仍然存在（防止误删）。

    Args:
        env: Android 环境接口。
        file_name: 文件名。
        directory_path: 目录路径。
        initial_files: 初始化时目录中的文件名列表。如果提供，会验证除了
            目标文件之外的其他文件仍然存在。

    Returns:
        True 如果验证通过，False 否则。
    """
    print(f"[DEBUG] Checking if file is deleted: {file_name} in {directory_path}")

    if file_exists(env, file_name, directory_path):
        print(f"[DEBUG] File still exists: {file_name}")
        return False

    # 检查其他文件是否被误删
    if initial_files is not None:
        other_files = [f for f in initial_files if f != file_name]
        for other in other_files:
            if not file_exists(env, other, directory_path):
                print(f"[DEBUG] Unexpected file deletion: {other} was also deleted")
                return False

    print(f"[DEBUG] File deletion validated: True")
    return True


def validate_file_moved(
    env: interface.AsyncEnv,
    file_name: str,
    source_path: str,
    destination_path: str,
) -> bool:
    """验证文件是否被正确移动。

    Args:
        env: Android 环境接口。
        file_name: 文件名。
        source_path: 源目录路径。
        destination_path: 目标目录路径。

    Returns:
        True 如果验证通过，False 否则。
    """
    print(f"[DEBUG] Checking if file moved: {file_name}")
    print(f"[DEBUG] Source: {source_path}")
    print(f"[DEBUG] Destination: {destination_path}")

    # 检查源目录中文件不存在
    if file_exists(env, file_name, source_path):
        print(f"[DEBUG] File still exists in source: {file_name}")
        return False

    # 检查目标目录中文件存在
    if not file_exists(env, file_name, destination_path):
        print(f"[DEBUG] File does not exist in destination: {file_name}")
        return False

    print(f"[DEBUG] File move validated: True")
    return True


def validate_file_renamed(
    env: interface.AsyncEnv,
    old_name: str,
    new_name: str,
    directory_path: str,
) -> bool:
    """验证文件是否被正确重命名。

    Args:
        env: Android 环境接口。
        old_name: 原文件名（精确匹配）。
        new_name: 新文件名（忽略大小写匹配）。
        directory_path: 目录路径。

    Returns:
        True 如果验证通过，False 否则。
    """
    print(f"[DEBUG] Checking if file renamed: {old_name} -> {new_name}")
    print(f"[DEBUG] Directory: {directory_path}")

    # 检查原文件名不存在（精确匹配）
    if file_exists(env, old_name, directory_path):
        print(f"[DEBUG] Old file still exists: {old_name}")
        return False

    # 检查新文件名是否存在（忽略大小写）
    files = get_files_in_directory(env, directory_path)
    file_names = [f.name for f in files]
    new_name_lower = new_name.lower()
    new_file_exists = any(f.lower() == new_name_lower for f in file_names)

    if not new_file_exists:
        print(f"[DEBUG] New file does not exist (case-insensitive): {new_name}")
        print(f"[DEBUG] Files in directory: {file_names}")
        return False

    print(f"[DEBUG] File rename validated: True")
    return True


def validate_directory_created(
    env: interface.AsyncEnv,
    directory_name: str,
    parent_path: str,
) -> bool:
    """验证目录是否被正确创建。

    Args:
        env: Android 环境接口。
        directory_name: 目录名。
        parent_path: 父目录路径。

    Returns:
        True 如果验证通过，False 否则。
    """
    new_path = file_utils.convert_to_posix_path(parent_path, directory_name)
    print(f"[DEBUG] Checking if directory exists: {new_path}")

    if not directory_exists(env, new_path):
        print(f"[DEBUG] Directory does not exist: {new_path}")
        return False

    print(f"[DEBUG] Directory creation validated: True")
    return True


def validate_directory_deleted(
    env: interface.AsyncEnv,
    directory_path: str,
) -> bool:
    """验证目录是否被正确删除。

    Args:
        env: Android 环境接口。
        directory_path: 目录路径。

    Returns:
        True 如果验证通过，False 否则。
    """
    print(f"[DEBUG] Checking if directory is deleted: {directory_path}")

    if directory_exists(env, directory_path):
        print(f"[DEBUG] Directory still exists: {directory_path}")
        return False

    print(f"[DEBUG] Directory deletion validated: True")
    return True


def validate_files_created(
    env: interface.AsyncEnv,
    files: list[dict],
    directory_path: str,
) -> bool:
    """验证多个文件是否被正确创建。

    Args:
        env: Android 环境接口。
        files: 文件列表，每个元素是包含 name 和可选 content 字段的字典。
        directory_path: 目录路径。

    Returns:
        True 如果验证通过，False 否则。
    """
    for file_data in files:
        file_name = file_data.get("name", "")
        expected_content = file_data.get("content")

        if not validate_file_created(
            env, file_name, directory_path, expected_content
        ):
            print(f"[DEBUG] Failed to validate file: {file_name}")
            return False

    print(f"[DEBUG] Multiple files creation validated: True")
    return True


def validate_files_deleted(
    env: interface.AsyncEnv,
    file_names: list[str],
    directory_path: str,
    initial_files: Optional[list[str]] = None,
) -> bool:
    """验证多个文件是否被正确删除。

    如果提供了 initial_files，还会检查是否只有目标文件被删除，
    其他文件仍然存在（防止误删）。

    Args:
        env: Android 环境接口。
        file_names: 文件名列表。
        directory_path: 目录路径。
        initial_files: 初始化时目录中的文件名列表。如果提供，会验证除了
            目标文件之外的其他文件仍然存在。

    Returns:
        True 如果验证通过，False 否则。
    """
    for file_name in file_names:
        if not validate_file_deleted(env, file_name, directory_path, initial_files):
            print(f"[DEBUG] Failed to validate file deletion: {file_name}")
            return False

    print(f"[DEBUG] Multiple files deletion validated: True")
    return True


def get_favorites(env: interface.AsyncEnv) -> list[sqlite_schema_utils.GenericRow]:
    """获取 Simple Gallery Pro 的收藏列表。

    Args:
        env: Android 环境接口。

    Returns:
        收藏记录列表。
    """
    try:
        favorites = sqlite_utils.get_rows_from_remote_device(
            table_name=_GALLERY_FAVORITES_TABLE,
            remote_db_file_path=_GALLERY_DB_PATH,
            row_type=sqlite_schema_utils.GenericRow,
            env=env,
        )
        print(f"[DEBUG] Found {len(favorites)} favorites in gallery database")
        return favorites
    except (ValueError, FileNotFoundError) as e:
        print(f"[DEBUG] Error querying gallery favorites database: {e}")
        return []


def _extract_favorite_ids(favorites: list[sqlite_schema_utils.GenericRow]) -> set[str]:
    """从收藏记录中提取每条记录的唯一标识。

    使用记录所有字段的键值对生成唯一字符串，按记录（行）为单位比较，
    避免同一记录的多个字段值被误判为多条收藏。

    Args:
        favorites: 收藏记录列表。

    Returns:
        每条记录的唯一标识集合。
    """
    ids = set()
    for fav in favorites:
        # GenericRow 通过 __dict__ 存储字段，用排序后的键值对生成唯一标识
        items = tuple(sorted(fav.__dict__.items()))
        ids.add(repr(items))
    return ids


def validate_image_favorited(
    env: interface.AsyncEnv,
    file_name: str,
    directory_path: str,
    before_favorites: Optional[list[sqlite_schema_utils.GenericRow]] = None,
) -> bool:
    """验证图片是否被正确收藏。

    Simple Gallery Pro 通过内部 SQLite 数据库的 favorites 表来标记收藏的图片。
    验证逻辑：查询 favorites 表，检查目标文件路径是否在收藏列表中。
    如果传入了 before_favorites，还会检查是否有其他图片被多收藏。

    Args:
        env: Android 环境接口。
        file_name: 文件名。
        directory_path: 目录路径。
        before_favorites: 任务执行前的收藏列表，用于检查是否有其他图片被多收藏。
            如果为 None 则不进行完整性检查。

    Returns:
        True 如果验证通过，False 否则。
    """
    print(f"[DEBUG] Checking if image is favorited: {file_name} in {directory_path}")

    # 首先检查文件是否存在
    if not file_exists(env, file_name, directory_path):
        print(f"[DEBUG] Image file does not exist: {file_name}")
        return False

    # 拼接完整文件路径
    full_path = f"{directory_path}/{file_name}"
    print(f"[DEBUG] Full path to check: {full_path}")

    try:
        # 查询 Simple Gallery Pro 的 favorites 表
        after_favorites = get_favorites(env)

        # 检查目标文件路径是否在收藏列表中
        target_found = False
        for fav in after_favorites:
            # favorites 表中的路径字段可能叫 path 或 medium_path
            fav_path = None
            for key in fav:
                val = str(getattr(fav, key, ''))
                if full_path in val or file_name in val:
                    fav_path = val
                    break
            if fav_path:
                print(f"[DEBUG] Image is favorited: {file_name} (matched: {fav_path})")
                target_found = True
                break

        if not target_found:
            print(f"[DEBUG] Image not found in favorites: {file_name}")
            return False

        # 检查是否有其他图片被多收藏
        if before_favorites is not None:
            before_ids = _extract_favorite_ids(before_favorites)
            after_ids = _extract_favorite_ids(after_favorites)
            new_ids = after_ids - before_ids
            print(f"[DEBUG] Before favorites count: {len(before_ids)}")
            print(f"[DEBUG] After favorites count: {len(after_ids)}")
            print(f"[DEBUG] Newly favorited count: {len(new_ids)}")

            # 新增的收藏记录中，每条都应该包含目标文件
            for new_id in new_ids:
                is_target = False
                for fav in after_favorites:
                    fav_repr = repr(tuple(sorted(fav.__dict__.items())))
                    if fav_repr == new_id:
                        for key in fav:
                            val = str(getattr(fav, key, ''))
                            if full_path in val or file_name in val:
                                is_target = True
                                break
                        break
                if not is_target:
                    print(f"[DEBUG] Unexpected favorite added: {new_id}")
                    return False

            print(f"[DEBUG] No unexpected favorites added")

        return True
    except (ValueError, FileNotFoundError) as e:
        print(f"[DEBUG] Error querying gallery favorites database: {e}")
        return False