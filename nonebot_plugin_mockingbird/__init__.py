import asyncio
import os
from pathlib import Path

import langid
import nonebot
from mockingbirdforuse import MockingBird
from mockingbirdforuse.log import logger as mocking_logger
from mockingbirdforuse.log import default_filter
from nonebot import Driver, export, on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.log import logger as nonebot_logger
from nonebot.params import ArgStr, CommandArg
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from nonebot.typing import T_State

from .config import MOCKINGBIRD_PATH, Config
from .data_source import get_ai_voice, is_number
from .download import check_resource, download_resource

__help__plugin_name__ = "MockingBird语音"
__des__ = "利用MockingBird生成语音并发送"
__cmd__ = f"""
触发方式：@Bot 说 [你想要bot说的话]
显示模型 显示所有模型
超级用户指令:
    修改模型 [序号]\[模型名称]
    重载模型 进行模型重载(并没有什么卵用，或许以后内存泄漏解决会有用？)
    调整/修改精度 修改语音合成精度
    调整/修改句长 修改语音合成最大句长
    更新模型 更新模型列表
""".strip()
__example__ = """
@真寻 说真寻可爱
修改模型 azusa
调整精度 9
调整句长 4
""".strip()
__usage__ = f"{__des__}\n\nUsage:\n{__cmd__}\n\nExamples:\n{__example__}"

driver: Driver = nonebot.get_driver()
export = export()

mockingbird_path = Path(MOCKINGBIRD_PATH)
mocking_logger = nonebot_logger  # 覆盖使用nonebot的logger
default_filter.level = driver.config.log_level

mockingbird = MockingBird()

@driver.on_startup
async def init_mockingbird():
    global part
    global export
    global mockingbird
    model_name = Config.get_config(config_name="model")
    model_path = mockingbird_path / model_name
    try:
        if not model_path.exists():
            mocking_logger.info("MockingBird 模型不存在...开始下载模型...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
        if not await check_resource(mockingbird_path, model_name):
            if await download_resource(mockingbird_path, model_name):
                mocking_logger.info("模型下载成功...")
            else:
                mocking_logger.error("模型下载失败，请检查网络...")
                return False
        mocking_logger.info("开始加载 MockingBird 模型...")
        mockingbird.load_model(
            Path(os.path.join(mockingbird_path, "encoder.pt")),
            Path(os.path.join(mockingbird_path, "g_hifigan.pt")),
            # Path(os.path.join(mockingbird_path, "wavernn.pt"))
        )
        mockingbird.set_synthesizer(Path(os.path.join(model_path, f"{model_name}.pt")))
        return True
    except Exception as e:
        return f"{type(e)}：{e}"

voice = on_command("说", aliases={"语音"}, block=True, rule=to_me(), priority=4)

view_model = on_command("显示所有模型", aliases={"MockingBird模型", "显示模型", "所有模型"}, block=True, priority=5)

change_model = on_command("修改模型", aliases={"MockingBird模型修改"}, block=True, permission=SUPERUSER, priority=5)

reload_mockingbird = on_command("重载模型", aliases={"MockingBird模型重载"}, block=True, permission=SUPERUSER, priority=5)

adjust_accuracy = on_command("调整语音精度", aliases={"调整精度", "修改精度"}, block=True, permission=SUPERUSER, priority=5)

adjust_steps = on_command("调整语音句长", aliases={"调整句长", "修改句长"}, block=True, permission=SUPERUSER, priority=5)

update_model_list = on_command("更新模型", aliases={"更新MockingBird", "模型更新"}, block=True, permission=SUPERUSER, priority=5)

@voice.handle()
async def _(state:T_State, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if args:
        state["words"] = args

@voice.got("words", prompt=f"想要让Bot说什么话呢?")
async def _(state: T_State,  words: str = ArgStr("words")):
    global part
    words = words.strip().replace('\n', '').replace('\r', '')
    if langid.classify(words)[0] == "ja":
        record = await get_ai_voice(words)
    else:
        record = await asyncio.get_event_loop().run_in_executor(
            None,
            mockingbird.synthesize,
            str(words),
            mockingbird_path / Config.get_config(config_name="model") / "record.wav",
            "HifiGan",
            0,
            Config.get_config(config_name="voice_accuracy"),
            Config.get_config(config_name="max_steps"),
        )
        record = MessageSegment.record(record)
    await voice.finish(MessageSegment.record(record))

@view_model.handle()
async def _():
    msg = "当前加载的模型为:{}\n".format(Config.get_config(config_name="model"))
    msg += "当前精度: {} , 最大句长: {}\n".format(Config.get_config(config_name="voice_accuracy"), Config.get_config(config_name="max_steps"))
    msg += "可以修改的模型列表:"
    for i, model in Config.model_list.items():
        msg += "\n{}. {} --- {}".format(i, model[0], model[1])
    await view_model.finish(msg)

@change_model.handle()
async def _(arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if is_number(args):
        args = Config.model_list.get(args)
        if args is None:
            await change_model.finish("该模型不存在...")
        else:
            args = args[0]
    models = []
    for model in Config.model_list.values():
        models.append(model[0])
    if args not in models:
        await change_model.finish("该模型不存在...")
    else:
        if args == Config.get_config(config_name="model"):
            await change_model.finish("该模型正在使用，请勿重复加载...")
        Config.set_config(config_name="model", value=args)
        msg = await init_mockingbird()
        if isinstance(msg, str):
            await change_model.finish(f"修改失败...错误信息:{msg}")
        else:
            await change_model.finish(f"修改MockingBird模型为{args}成功...")

@reload_mockingbird.handle()
async def reload_model():
    msg = await init_mockingbird()
    if isinstance(msg, str):
        await reload_mockingbird.finish(f"重载失败...错误信息:{msg}")
    else:
        await reload_mockingbird.finish(f"重载MockingBird模型成功...")

@adjust_accuracy.handle()
async def _(arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if not is_number(args):
        await adjust_accuracy.finish("请输入数字...")
    num = int(args)
    if num > 2 and num < 10:
        Config.set_config(config_name="voice_accuracy", value=num)
        msg = await init_mockingbird()
        if isinstance(msg, str):
            await adjust_accuracy.finish(f"调整失败...错误信息:{msg}")
        await adjust_accuracy.finish(f"已修改精度为: {num}")
    else:
        await adjust_accuracy.finish("请输入3-9以内的数字！")
        
@adjust_steps.handle()
async def _(arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if not is_number(args):
        await adjust_steps.finish("请输入数字...")
    num = int(args)
    if num > 0 and num < 11:
        Config.set_config(config_name="max_steps", value=num)
        msg = await init_mockingbird()
        if isinstance(msg, str):
            await adjust_steps.finish(f"调整失败...错误信息:{msg}")
        await adjust_steps.finish(f"已修改最大句长为: {num}")
    else:
        await adjust_steps.finish("请输入1-10以内的数字！")

@update_model_list.handle()
async def _():
    msg = Config.update_model_list()
    if isinstance(msg, str):
        update_model_list.finish(msg)
    else:
        update_model_list.finish("模型列表更新成功!")
