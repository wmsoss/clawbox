from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import httpx

from backend.dependencies import get_db
from backend.models import InstalledSkill
from backend.schemas import SkillInstallDTO
from backend.services.skill_parser import SkillParser, install_skill, uninstall_skill
from backend.config import settings

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])
logger = logging.getLogger(__name__)

# GitHub 仓库地址
AWESOME_SKILLS_URL = "https://raw.githubusercontent.com/VoltAgent/awesome-openclaw-skills/main/README.md"

@router.get("/list")
async def list_skills(
    db: AsyncSession = Depends(get_db)
):
    """
    Get the list of all available skills from the registry and merge with locally installed status.
    """
    try:
        # 1. Fetch README from GitHub
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(AWESOME_SKILLS_URL, follow_redirects=True)
            response.raise_for_status()
            raw_readme = response.text

        # 2. Parse available skills from README
        parser = SkillParser()
        cards = parser.parse_readme(raw_readme)

        # 2. Get installed skills from DB
        result = await db.execute(select(InstalledSkill))
        installed_skills = result.scalars().all()
        installed_map = {skill.name: skill for skill in installed_skills}

        # 3. Group cards by category and merge install status
        category_map = {}
        for card in cards:
            if card.category not in category_map:
                category_map[card.category] = []

            # 检查是否已安装 (从 repo_url 提取技能名称)
            skill_name = card.repo_url.rstrip("/").split("/")[-1]
            is_installed = False
            if skill_name in installed_map:
                db_skill = installed_map[skill_name]
                is_installed = db_skill.is_active

            category_map[card.category].append({
                "name": card.name,
                "repo_url": card.repo_url,
                "description": card.description,
                "is_installed": is_installed
            })

        # 4. Convert to sections list
        res_sections = []
        for category, skills in category_map.items():
            res_sections.append({
                "name": category,
                "description": "",
                "skills": skills
            })

        return {"sections": res_sections}

    except HTTPException:
        # 重新抛出 HTTPException
        raise
    except Exception as e:
        logger.error(f"Failed to list skills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch skills: {str(e)}")

@router.post("/install")
async def api_install_skill(
    dto: SkillInstallDTO,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Install a new skill. Uses background tasks to avoid blocking the HTTP response.
    """
    # Simply call the install_skill function from the service
    # Because it might take time (git clone), we run it in the background if we want true async,
    # but the whitepaper §9.2 suggests atomic replacement right away.
    # For simplicity and ease of UI polling, we'll await it directly here. 
    # In a full production system, we'd use BackgroundTasks and a status endpoint.
    try:
        success = await install_skill(dto.repo_url, dto.name, db)
        if success:
            return {"status": "ok", "message": f"Skill '{dto.name}' installed successfully."}
        else:
            # install_skill internally raises exceptions on failure, but just in case:
            raise HTTPException(status_code=500, detail="Installation failed silently.")
    except Exception as e:
        logger.error(f"Skill installation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{name}")
async def api_uninstall_skill(
    name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Uninstall an existing skill.
    """
    try:
        success = await uninstall_skill(name, db)
        if success:
            return {"status": "ok", "message": f"Skill '{name}' uninstalled successfully."}
        else:
            raise HTTPException(status_code=500, detail="Uninstallation failed silently.")
    except Exception as e:
        logger.error(f"Skill uninstallation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
