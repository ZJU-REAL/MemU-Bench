

"""Tasks for recipes app."""

import dataclasses
import random
import time
from typing import Any
from android_world.env import adb_utils
from android_world.env import device_constants
from android_world.env import interface
from android_world.env import representation_utils
from android_world.task_evals.common_validators import sqlite_validators
from android_world.task_evals.custom_validators import llm_as_judge
from android_world.task_evals.utils import sqlite_schema_utils
from android_world.task_evals.utils import sqlite_utils
from android_world.task_evals.utils import user_data_generation
from android_world.utils import file_utils


_DB_PATH = '/data/data/com.flauschcode.broccoli/databases/broccoli'
_TABLE_NAME = 'recipes'


RECIPE_VALIDATION_PROMPT_TEMPLATE = """You are a recipe validation assistant. Please determine whether the actual added recipe meets the task requirements.

Task Requirements (Expected Recipe):
{expected_fields}

Actual Added Recipe:
{actual_fields}

Judgment Rules:
1. Judge holistically - consider the entire recipe as a whole, not just individual fields
2. The actual recipe is considered correct if it conveys the same core information as the expected recipe
3. Extra fields in the actual recipe are acceptable IF they are:
   - Repetitions or rephrasings of information already present in other fields
   - Natural summaries of the directions or ingredients
   - Redundant mentions of servings, title, or other existing info
4. Missing fields in the actual recipe are acceptable IF the information is implied by other fields
5. Examples of SUCCESS:
   - Expected: Description="pasta dish", Actual: Description="A simple pasta dish" -> SUCCESS
   - Expected: Description="A delicious cake", Actual: Description="A delicious chocolate cake with frosting" -> SUCCESS (core info "delicious cake" is present, "chocolate" and "frosting" are minor additions)
6. Examples of FAILURE:
   - Expected: Ingredients="eggs, flour", Actual: Ingredients="eggs" -> FAILURE (missing key ingredient)
   - Expected: Directions="boil water", Actual: Directions="fry in pan" -> FAILURE (completely different cooking method)
   - Expected: Title="Apple Pie", Actual: Title="Orange Juice" -> FAILURE (completely different recipe)
7. Focus on semantic equivalence at the recipe level, not strict field-by-field matching
"""

RECIPE_FIELD_PROMPT = """You are a recipe validation assistant. Please determine whether the actual field value meets the requirements.

Expected Value:
{expected_value}

Actual Value:
{actual_value}

Judgment Rules:
1. Use semantic matching - the actual value should convey the same core information as the expected value
2. Wording, style, and minor details can differ, but the essential content must be equivalent
3. Missing key information from the expected value should be judged as Failure
4. Extra information that doesn't contradict the expected value is acceptable if it's natural elaboration
5. Completely different content should be judged as Failure

Please reply in the following format:
Result: [Success/Failure]
Explanation: [Brief explanation of the judgment]
"""


# ============================================================================
# Standalone validation functions for recipe operations
# ============================================================================


def _recipe_matches(recipe: sqlite_schema_utils.Recipe, expected: dict) -> bool:
    """Check if a recipe matches expected criteria.

    All fields use fuzzy (partial, case-insensitive) matching.

    Args:
        recipe: The actual recipe from database.
        expected: Expected recipe criteria with fields like:
            - title: str
            - description: str
            - servings: str
            - preparationTime: str
            - source: str
            - ingredients: str
            - directions: str
            - favorite: int/str
            - recipeId: int/str

    Returns:
        True if recipe matches all criteria, False otherwise.
    """
    def _fuzzy_match(actual: str, expected_val: str) -> bool:
        """Check if expected is contained in actual (case-insensitive)."""
        actual_clean = actual.lower().strip()
        expected_clean = str(expected_val).lower().strip()
        return expected_clean in actual_clean or actual_clean in expected_clean

    # Check title
    if 'title' in expected:
        if not _fuzzy_match(recipe.title, expected['title']):
            return False

    # Check description
    if 'description' in expected:
        if not _fuzzy_match(recipe.description, expected['description']):
            return False

    # Check servings
    if 'servings' in expected:
        if not _fuzzy_match(recipe.servings, expected['servings']):
            return False

    # Check preparation time
    if 'preparationTime' in expected:
        if not _fuzzy_match(recipe.preparationTime, expected['preparationTime']):
            return False

    # Check source
    if 'source' in expected:
        if not _fuzzy_match(recipe.source, expected['source']):
            return False

    # Check ingredients
    if 'ingredients' in expected:
        if not _fuzzy_match(recipe.ingredients, expected['ingredients']):
            return False

    # Check directions
    if 'directions' in expected:
        if not _fuzzy_match(recipe.directions, expected['directions']):
            return False

    # Check favorite (convert to string for fuzzy match)
    if 'favorite' in expected:
        if not _fuzzy_match(str(recipe.favorite), str(expected['favorite'])):
            return False

    # Check recipeId (convert to string for fuzzy match)
    if 'recipeId' in expected:
        if not _fuzzy_match(str(recipe.recipeId), str(expected['recipeId'])):
            return False

    return True


def get_recipes(env: interface.AsyncEnv) -> list[sqlite_schema_utils.Recipe]:
    """Get all recipes from the Broccoli app database.

    Args:
        env: Android environment interface.

    Returns:
        List of Recipe objects from the database. Returns empty list if database doesn't exist.
    """
    try:
        recipes = sqlite_utils.get_rows_from_remote_device(
            _TABLE_NAME,
            _DB_PATH,
            sqlite_schema_utils.Recipe,
            env,
        )
        print(f"[DEBUG] Found {len(recipes)} recipes in database")
        for i, recipe in enumerate(recipes):
            print(f"[DEBUG] Recipe {i+1}: {recipe.title} (ID: {recipe.recipeId})")
        return recipes
    except (FileNotFoundError, ValueError) as e:
        print(f"[DEBUG] Database not found or empty: {e}")
        return []


def clear_recipes(env: interface.AsyncEnv) -> None:
    """Clear all recipes from the Broccoli app.

    Args:
        env: Android environment interface.
    """
    from android_world.env import adb_utils
    adb_utils.clear_app_data('com.flauschcode.broccoli', env.controller)
    print("[DEBUG] All recipes cleared")


def validate_recipe_added(
    env: interface.AsyncEnv,
    goal: str,
    before_recipes: list[sqlite_schema_utils.Recipe],
    expected_title: str,
    expected_description: str | None = None,
    expected_servings: str | None = None,
    expected_preparationTime: str | None = None,
    expected_ingredients: str | None = None,
    expected_directions: str | None = None,
) -> bool:
    """Validate that a recipe was added to the database using LLM judge.

    Args:
        env: Android environment interface.
        goal: The task goal describing what the agent was supposed to do.
        before_recipes: List of recipes before the operation.
        expected_title: Expected recipe title.
        expected_description: Expected description (optional).
        expected_servings: Expected servings (optional).
        expected_preparationTime: Expected preparation time (optional).
        expected_ingredients: Expected ingredients (optional).
        expected_directions: Expected directions (optional).

    Returns:
        True if a matching recipe was added according to LLM judgment, False otherwise.
    """
    after_recipes = get_recipes(env)

    print(f"[DEBUG] Before recipes: {len(before_recipes)}")
    print(f"[DEBUG] After recipes: {len(after_recipes)}")

    # Find new recipes
    before_ids = {r.recipeId for r in before_recipes}
    new_recipes = [r for r in after_recipes if r.recipeId not in before_ids]

    print(f"[DEBUG] New recipes count: {len(new_recipes)}")

    if not new_recipes:
        print("[DEBUG] No new recipes found, returning False")
        return False

    # Check that only one recipe was added (validate count correctness)
    if len(new_recipes) != 1:
        print(f"[DEBUG] Expected 1 new recipe, but found {len(new_recipes)}. Validation failed.")
        return False

    # Print details of new recipes
    print(f"[DEBUG] ========== New recipes ==========")
    for i, recipe in enumerate(new_recipes):
        print(f"[DEBUG] New recipe {i+1}:")
        print(f"[DEBUG]   title: {recipe.title}")
        print(f"[DEBUG]   description: {recipe.description}")
        print(f"[DEBUG]   servings: {recipe.servings}")
        print(f"[DEBUG]   preparationTime: {recipe.preparationTime}")
        print(f"[DEBUG]   ingredients: {recipe.ingredients}")
        print(f"[DEBUG]   directions: {recipe.directions[:100]}...")

    # Take the first new recipe for validation (assuming single recipe addition)
    actual_recipe = new_recipes[0]

    # Check if expected fields have values but actual fields are missing - direct failure
    if expected_description is not None and actual_recipe.description is None:
        print("[DEBUG] Expected description provided but actual description is missing - validation failed")
        return False
    if expected_servings is not None and actual_recipe.servings is None:
        print("[DEBUG] Expected servings provided but actual servings is missing - validation failed")
        return False
    if expected_preparationTime is not None and actual_recipe.preparationTime is None:
        print("[DEBUG] Expected preparationTime provided but actual preparationTime is missing - validation failed")
        return False
    if expected_ingredients is not None and actual_recipe.ingredients is None:
        print("[DEBUG] Expected ingredients provided but actual ingredients is missing - validation failed")
        return False
    if expected_directions is not None and actual_recipe.directions is None:
        print("[DEBUG] Expected directions provided but actual directions is missing - validation failed")
        return False

    # Build the prompt for LLM judge - only include fields that expected specifies
    expected_fields = []
    actual_fields = []

    expected_fields.append(f"- Title: {expected_title}")
    actual_fields.append(f"- Title: {actual_recipe.title or 'Not specified'}")

    if expected_description is not None:
        expected_fields.append(f"- Description: {expected_description}")
        actual_fields.append(f"- Description: {actual_recipe.description or ''}")

    if expected_servings is not None:
        expected_fields.append(f"- Servings: {expected_servings}")
        actual_fields.append(f"- Servings: {actual_recipe.servings or ''}")

    if expected_preparationTime is not None:
        expected_fields.append(f"- Preparation Time: {expected_preparationTime}")
        actual_fields.append(f"- Preparation Time: {actual_recipe.preparationTime or ''}")

    if expected_ingredients is not None:
        expected_fields.append(f"- Ingredients: {expected_ingredients}")
        actual_fields.append(f"- Ingredients: {actual_recipe.ingredients or ''}")

    if expected_directions is not None:
        expected_fields.append(f"- Directions: {expected_directions}")
        actual_fields.append(f"- Directions: {actual_recipe.directions or ''}")

    prompt = RECIPE_VALIDATION_PROMPT_TEMPLATE.format(
        expected_fields="\n".join(expected_fields),
        actual_fields="\n".join(actual_fields),
    )

    print(f"[DEBUG] Calling LLM to validate recipe...")
    is_match, explanation = llm_as_judge.llm_judge(goal, prompt)
    print(f"[DEBUG] LLM judgment: {is_match}, Explanation: {explanation}")

    return is_match



def validate_recipe_deleted(
    env: interface.AsyncEnv,
    before_recipes: list[sqlite_schema_utils.Recipe],
    expected: dict,
) -> bool:
    """Validate that a recipe was deleted from the database.

    Args:
        env: Android environment interface.
        before_recipes: List of recipes before the operation.
        expected: Expected recipe criteria of the deleted recipe.

    Returns:
        True if a matching recipe was deleted, False otherwise.
    """
    after_recipes = get_recipes(env)

    print(f"[DEBUG] Before recipes: {len(before_recipes)}")
    print(f"[DEBUG] After recipes: {len(after_recipes)}")
    print(f"[DEBUG] Expected deleted: {expected}")

    # Check that exactly one recipe was deleted
    if len(after_recipes) != len(before_recipes) - 1:
        print(f"[DEBUG] Recipe count changed from {len(before_recipes)} to {len(after_recipes)}, "
              f"expected {len(before_recipes) - 1}. Other recipes may have been deleted.")
        return False

    # Find deleted recipes
    after_ids = {r.recipeId for r in after_recipes}
    deleted_recipes = [r for r in before_recipes if r.recipeId not in after_ids]

    print(f"[DEBUG] Deleted recipes count: {len(deleted_recipes)}")

    # Print details of deleted recipes
    for i, recipe in enumerate(deleted_recipes):
        print(f"[DEBUG] Deleted recipe {i+1}: {recipe.title} (ID: {recipe.recipeId})")

    # Check if the deleted recipe matches expected criteria
    for recipe in deleted_recipes:
        if _recipe_matches(recipe, expected):
            print(f"[DEBUG] Recipe deleted validated: True")
            print(f"[DEBUG] Deleted recipe: {recipe.title}")
            return True

    print(f"[DEBUG] No matching recipe found in deleted recipes")
    return False




def validate_recipe_modified(
    env: interface.AsyncEnv,
    before_recipes: list[sqlite_schema_utils.Recipe],
    expected_title: str,
    expected_field: str,
    expected_value: str,
) -> bool:
    """Validate that a recipe's field was correctly modified using LLM judge.

    Validation logic:
    1. Check recipe count is the same before and after (modification doesn't change count)
    2. Find the recipe by exact title match (not fuzzy) to confirm it's the same recipe
    3. Use LLM to validate the modified field content semantically

    Args:
        env: Android environment interface.
        before_recipes: List of recipes before the operation.
        expected_title: Expected recipe title to identify the recipe.
        expected_field: The field that should be modified (e.g., 'directions').
        expected_value: The expected new value for the field.

    Returns:
        True if the recipe field was modified correctly according to LLM judgment, False otherwise.
    """
    after_recipes = get_recipes(env)

    print(f"[DEBUG] Before recipes count: {len(before_recipes)}")
    print(f"[DEBUG] After recipes count: {len(after_recipes)}")

    # Step 1: Check recipe count is the same
    if len(before_recipes) != len(after_recipes):
        print(f"[DEBUG] Recipe count changed ({len(before_recipes)} -> {len(after_recipes)}). "
              f"This indicates addition/deletion, not modification. Validation failed.")
        return False

    # Step 2: Find the recipe by exact title match
    target_recipe = None
    for recipe in after_recipes:
        if recipe.title == expected_title:
            target_recipe = recipe
            break

    if not target_recipe:
        print(f"[DEBUG] No recipe found with exact title: {expected_title}")
        return False

    # Get the actual value of the modified field
    actual_value = getattr(target_recipe, expected_field, None)
    if actual_value is None:
        actual_value = "Not specified"

    print(f"[DEBUG] Recipe: {target_recipe.title}")
    print(f"[DEBUG] Expected {expected_field}: {expected_value}")
    print(f"[DEBUG] Actual {expected_field}: {actual_value[:100] if actual_value else 'N/A'}...")

    # Build the prompt for LLM judge
    prompt = RECIPE_FIELD_PROMPT.format(
        expected_value=expected_value,
        actual_value=actual_value,
    )

    print(f"[DEBUG] Calling LLM to validate recipe modification...")
    is_match, explanation = llm_as_judge.llm_judge("", prompt)
    print(f"[DEBUG] LLM judgment: {is_match}, Explanation: {explanation}")

    return is_match




def validate_recipe_exists(
    env: interface.AsyncEnv,
    expected: dict,
) -> bool:
    """Validate that a recipe matching criteria exists in the database.

    Args:
        env: Android environment interface.
        expected: Expected recipe criteria.

    Returns:
        True if a matching recipe exists, False otherwise.
    """
    recipes = get_recipes(env)

    print(f"[DEBUG] Checking if recipe exists: {expected}")
    print(f"[DEBUG] Total recipes in database: {len(recipes)}")

    for recipe in recipes:
        if _recipe_matches(recipe, expected):
            print(f"[DEBUG] Recipe exists validated: True")
            print(f"[DEBUG] Matched recipe: {recipe.title} (ID: {recipe.recipeId})")
            return True

    print(f"[DEBUG] No matching recipe found")
    return False


def validate_recipe_opened(
    env: interface.AsyncEnv,
    expected_title: str,
    fuzzy_match: bool = True,
    required_texts: list[str] | None = None,
) -> bool:
    """Validate that a specific recipe is currently open and displayed in the foreground.

    Checks that:
    1. The Broccoli recipe app is in the foreground.
    2. The expected recipe title appears in the current UI elements.
    3. All required texts appear in the UI elements (if provided).

    Args:
        env: Android environment interface.
        expected_title: The expected recipe title to look for in the UI.
        fuzzy_match: If True, uses case-insensitive partial matching;
            if False, requires exact match.
        required_texts: Optional list of texts that must also appear in the UI
            to confirm the recipe is fully opened (e.g., "Ingredients", "Directions").

    Returns:
        True if the recipe is currently open in the foreground, False otherwise.
    """
    # Check that the Broccoli app is in the foreground
    current_activity = env.foreground_activity_name
    if not current_activity or 'broccoli' not in current_activity.lower():
        print(f"[DEBUG] Broccoli app is not in the foreground. "
              f"Current activity: {current_activity}")
        return False

    print(f"[DEBUG] Broccoli app is in foreground: {current_activity}")

    # Wait briefly for UI to stabilize
    time.sleep(1.0)

    # Get UI elements, trying uiautomator dump first then falling back to env.get_state()
    try:
        xml_dump = adb_utils.uiautomator_dump(env.controller)
        ui_elements = representation_utils.xml_dump_to_ui_elements(xml_dump)
        print(f"[DEBUG] Got {len(ui_elements)} UI elements from uiautomator dump")
    except Exception as e:
        print(f"[DEBUG] uiautomator dump failed: {e}, falling back to env.get_state()")
        state = env.get_state(wait_to_stabilize=False)
        ui_elements = state.ui_elements

    # Search for the recipe title in UI elements
    if fuzzy_match:
        expected_lower = expected_title.lower().strip()

    title_found = False

    for element in ui_elements:
        # Check text field
        if element.text:
            if fuzzy_match:
                if expected_lower in element.text.lower() or element.text.lower() in expected_lower:
                    print(f"[DEBUG] Recipe title found in UI text: '{element.text}' "
                          f"matches expected: '{expected_title}'")
                    title_found = True
                    break
            else:
                if element.text.strip() == expected_title.strip():
                    print(f"[DEBUG] Recipe title found in UI text: '{element.text}' "
                          f"exactly matches expected: '{expected_title}'")
                    title_found = True
                    break

        # Check content_description field
        if element.content_description:
            if fuzzy_match:
                if expected_lower in element.content_description.lower() or element.content_description.lower() in expected_lower:
                    print(f"[DEBUG] Recipe title found in content_description: "
                          f"'{element.content_description}' matches expected: '{expected_title}'")
                    title_found = True
                    break
            else:
                if element.content_description.strip() == expected_title.strip():
                    print(f"[DEBUG] Recipe title found in content_description: "
                          f"'{element.content_description}' exactly matches expected: '{expected_title}'")
                    title_found = True
                    break

    if not title_found:
        # Recipe title not found in UI — print debug info
        print(f"[DEBUG] Recipe title '{expected_title}' not found in UI elements.")
        print(f"[DEBUG] UI elements ({len(ui_elements)} total):")
        for i, element in enumerate(ui_elements):
            text = element.text or ""
            desc = element.content_description or ""
            if text or desc:
                print(f"[DEBUG]   [{i}] text='{text}', desc='{desc}'")
        return False

    # Check required texts if provided
    if required_texts:
        print(f"[DEBUG] Checking required texts: {required_texts}")
        for required_text in required_texts:
            if not _check_text_in_ui_elements(ui_elements, required_text, fuzzy_match):
                print(f"[DEBUG] Required text '{required_text}' not found in UI elements")
                return False
            print(f"[DEBUG] Required text '{required_text}' found")

    print("[DEBUG] Recipe opened validation passed")
    return True


def _check_text_in_ui_elements(
    ui_elements: list,
    text: str,
    fuzzy_match: bool = True,
) -> bool:
    """Check if a specific text appears in any UI element.

    Args:
        ui_elements: List of UI elements to search.
        text: The text to look for.
        fuzzy_match: If True, uses case-insensitive partial matching.

    Returns:
        True if the text is found, False otherwise.
    """
    text_lower = text.lower().strip()

    for element in ui_elements:
        # Check text field
        if element.text:
            if fuzzy_match:
                if text_lower in element.text.lower():
                    return True
            else:
                if element.text.strip() == text:
                    return True

        # Check content_description field
        if element.content_description:
            if fuzzy_match:
                if text_lower in element.content_description.lower():
                    return True
            else:
                if element.content_description.strip() == text:
                    return True

    return False
