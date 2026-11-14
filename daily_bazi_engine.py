# -*- coding: utf-8 -*-
"""
================================================================================
每日八字动态推演与智能推送引擎 (Daily Bazi Deduction & Push Engine) - v3.0 终极完全体
--------------------------------------------------------------------------------
【理论基石】：
  1. 《三命通会》（明·万民英）：骨肉躯干（干支刑冲合害、太岁岁破、神煞值日、五鼠遁起时法）
  2. 《滴天髓》（清·任铁樵）：动力神经（五行旺衰力学、生克心理学、气象调候平衡）
  3. 《了凡四训》（明·袁了凡）：知行闭环（每日功过格微习惯实修，化被动宿命为主动改命）
  *(坚决剔除管十年社会阶层的《子平真诠》与管四时宏观调候的《穷通宝鉴》)*

【v3.0 九大终极升级 (The 9 Ultimate Upgrades)】：
  1. 消除文案覆盖 Bug：财运与感情状态采用优先级列表累加合成，严禁后规则抹除前规则的高危预警。
  2. 日间吉时过滤 + 日破时一票否决：黄金效率时严格在日间活动窗口 (07:00-21:00) 择优，
     且流时若与流日相冲（日破时）直接重扣 6 分剔除，夜间吉时单独作为静思复盘参考。
  3. 纳入流年太岁维度：自动识别“岁破大耗日”（如丙午年逢子日冲太岁）与“岁日伏吟”。
  4. 60甲子全天干、全地支、天干五合 100% 映射：补齐壬/甲/乙/丙/丁天干、寅/卯/丑/未地支、
     甲己合/丁壬合等全部规则，彻底告别死板兜底文案。
  5. 十年大运时间轴自适应：内置 1991-2060 完整大运表，2031年自动由【壬申】切换至【癸酉】。
  6. 四象多维动态调候养生：结合流日五行与地支燥湿，细分为四大动态调候养生矩阵。
  7. 《了凡四训》功过格每日微修行：根据当日十神与刑冲，自动生成破财化慈、忍辱止嗔等改命动作。
  8. iOS Bark 原生高颜值纯文本排版：去除裸露的 ### 与 ** 符号，专为手机锁屏与通知阅读优化。
  9. 动态分级提示音与时效穿透：RED 级自动启用 timeSensitive 突破勿扰模式 + 警示音。
================================================================================
"""

import os
import sys
import math
import time
import json
import argparse
import urllib.request
from datetime import datetime, date, timedelta, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from lunar_python import Solar, Lunar
except ImportError:
    print("[Error] 请先安装 lunar_python 库: pip install lunar_python")
    sys.exit(1)


BEIJING_TZ = timezone(timedelta(hours=8))
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bark_config.json")


def get_beijing_today() -> date:
    """获取当前精准的北京时间日期（规避海外云端服务器默认UTC时区偏差）"""
    return datetime.now(BEIJING_TZ).date()


# ==============================================================================
# 1. 命主先天基准数据模型与大运时间轴
# ==============================================================================
@dataclass
class NativeProfile:
    name: str = "坤哥"
    gender: str = "男"
    birth_solar: str = "1984-04-14 11:45"
    birth_location: str = "贵州贵阳"
    longitude: float = 106.63  # 贵阳东经度
    latitude: float = 26.65    # 贵阳纬度

    # 四柱原局干支
    year_gan: str = "甲"
    year_zhi: str = "子"
    month_gan: str = "戊"
    month_zhi: str = "辰"
    day_gan: str = "戊"
    day_zhi: str = "寅"
    hour_gan: str = "丁"
    hour_zhi: str = "巳"

    # 命盘核心属性
    day_master: str = "戊"  # 戊土偏旺 (56.4分)
    favorable_elements: List[str] = field(default_factory=lambda: ["金", "水"])
    unfavorable_elements: List[str] = field(default_factory=lambda: ["火", "土"])

    def get_decade_luck(self, target_year: int) -> Tuple[str, str, str]:
        """
        根据流年年份动态返回命主当前所处的大运干支与周期说明
        实现一次编写、终身跨运自适应
        """
        if target_year < 2001:
            return ("己", "巳", "1991-2000 己巳大运")
        elif target_year < 2011:
            return ("庚", "午", "2001-2010 庚午大运")
        elif target_year < 2021:
            return ("辛", "未", "2011-2020 辛未大运")
        elif target_year < 2031:
            return ("壬", "申", "2021-2030 壬申大运")
        elif target_year < 2041:
            return ("癸", "酉", "2031-2040 癸酉大运")
        elif target_year < 2051:
            return ("甲", "戌", "2041-2050 甲戌大运")
        else:
            return ("乙", "亥", "2051-2060 乙亥大运")


# ==============================================================================
# 2. 命理基础常量与天文动力学表
# ==============================================================================
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

GAN_ELEMENTS = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"
}
ZHI_ELEMENTS = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"
}

# 戊土日元的十神映射
WU_TEN_GODS = {
    "甲": "七杀", "乙": "正官",
    "丙": "偏印", "丁": "正印",
    "戊": "比肩", "己": "劫财",
    "庚": "食神", "辛": "伤官",
    "壬": "偏财", "癸": "正财"
}

# 地支六冲双向映射表
ZHI_CLASH_MAP = {
    "子": "午", "午": "子",
    "丑": "未", "未": "丑",
    "寅": "申", "申": "寅",
    "卯": "酉", "酉": "卯",
    "辰": "戌", "戌": "辰",
    "巳": "亥", "亥": "巳"
}

# 天干相冲映射表
GAN_CLASH_MAP = {
    "甲": "庚", "庚": "甲",
    "乙": "辛", "辛": "乙",
    "丙": "壬", "壬": "丙",
    "丁": "癸", "癸": "丁"
}

# 月令五行旺衰系数表 (Wang-Xiang-Xiu-Qiu-Si)
MONTH_ENERGY_COEFFICIENT = {
    "寅": {"木": 1.30, "火": 1.15, "水": 0.85, "金": 0.70, "土": 0.55},
    "卯": {"木": 1.30, "火": 1.15, "水": 0.85, "金": 0.70, "土": 0.55},
    "巳": {"火": 1.30, "土": 1.15, "木": 0.85, "水": 0.70, "金": 0.55},
    "午": {"火": 1.30, "土": 1.15, "木": 0.85, "水": 0.70, "金": 0.55},
    "申": {"金": 1.30, "水": 1.15, "土": 0.85, "火": 0.70, "木": 0.55},
    "酉": {"金": 1.30, "水": 1.15, "土": 0.85, "火": 0.70, "木": 0.55},
    "亥": {"水": 1.30, "木": 1.15, "金": 0.85, "土": 0.70, "火": 0.55},
    "子": {"水": 1.30, "木": 1.15, "金": 0.85, "土": 0.70, "火": 0.55},
    "辰": {"土": 1.25, "金": 1.10, "火": 0.85, "木": 0.75, "水": 0.90},
    "戌": {"土": 1.25, "金": 1.10, "火": 0.85, "木": 0.70, "水": 0.60},
    "丑": {"土": 1.25, "金": 1.10, "火": 0.85, "木": 0.70, "水": 0.90},
    "未": {"土": 1.25, "金": 1.10, "火": 0.90, "木": 0.70, "水": 0.60}
}

SEVERITY_ORDER = {
    "GREEN": 1,
    "BLUE": 2,
    "ORANGE": 3,
    "RED": 4
}


# ==============================================================================
# 3. 最高风险锁存器 (Max-Severity Latch)
# ==============================================================================
class SeverityLatch:
    """最高风险锁存器：保证高危熔断无法被后续低危或吉象逆向降级"""
    def __init__(self, initial_level: str = "GREEN"):
        self._level = initial_level
        self._latch_reason = ""

    @property
    def level(self) -> str:
        return self._level

    @property
    def latch_reason(self) -> str:
        return self._latch_reason

    def update(self, candidate_level: str, reason: str):
        if SEVERITY_ORDER[candidate_level] > SEVERITY_ORDER[self._level]:
            self._level = candidate_level
            self._latch_reason = reason


# ==============================================================================
# 4. 全动态天文与微观动力学引擎 (v3.0)
# ==============================================================================
class DailyBaziEngine:
    def __init__(self, profile: NativeProfile):
        self.profile = profile

    def calculate_equation_of_time(self, target_date: date) -> float:
        """基于 NOAA 算法计算均时差 (EOT)"""
        day_of_year = target_date.timetuple().tm_yday
        b = math.radians((360.0 / 365.25) * (day_of_year - 81))
        return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    def calculate_total_solar_offset_minutes(self, target_date: date) -> float:
        """高精度真太阳时综合偏差 = 经度差修正 + 均时差 EOT"""
        lon_offset = (self.profile.longitude - 120.0) * 4.0
        eot = self.calculate_equation_of_time(target_date)
        return lon_offset + eot

    def format_solar_time(self, bj_time_str: str, offset_minutes: float) -> str:
        """根据北京时间 HH:MM 和总偏差生成贵阳真太阳时 HH:MM"""
        h, m = map(int, bj_time_str.split(":"))
        dt = datetime(2026, 1, 1, h, m) + timedelta(minutes=offset_minutes)
        return dt.strftime("%H:%M")

    def get_lunar_day_data(self, target_date: date) -> Dict:
        """获取目标日期的精确干支时令信息"""
        solar = Solar.fromYmd(target_date.year, target_date.month, target_date.day)
        lunar = solar.getLunar()
        return {
            "year": target_date.year,
            "solar_date": target_date.strftime("%Y-%m-%d"),
            "lunar_text": f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}",
            "year_gz": lunar.getYearInGanZhiExact(),
            "month_gz": lunar.getMonthInGanZhiExact(),
            "day_gz": lunar.getDayInGanZhiExact(),
        }

    def calculate_wu_shu_dun_hours(self, day_gan: str, day_zhi: str, offset_minutes: float) -> List[Dict]:
        """
        五鼠遁日上起时公式全天扫描 (v3.0 升级版)：
        1. 区分日间活动窗口 (07:00-21:00: 辰巳午未申酉戌) 与夜间休息窗口；
        2. 增加“流时 vs 流日”相冲（日破凶时）与天克地冲的一票否决扣分；
        3. 评估流时与原局的刑冲合会。
        """
        start_gan_map = {
            "甲": "甲", "己": "甲",
            "乙": "丙", "庚": "丙",
            "丙": "戊", "辛": "戊",
            "丁": "庚", "壬": "庚",
            "戊": "壬", "癸": "壬"
        }
        start_gan = start_gan_map.get(day_gan, "甲")
        start_gan_idx = TIAN_GAN.index(start_gan)

        standard_hour_slots = [
            ("子时", "23:00", "01:00", False, "早子时 00:00-01:00 适用，23:00 后按次日看"),
            ("丑时", "01:00", "03:00", False, ""),
            ("寅时", "03:00", "05:00", False, ""),
            ("卯时", "05:00", "07:00", False, ""),
            ("辰时", "07:00", "09:00", True, ""),
            ("巳时", "09:00", "11:00", True, ""),
            ("午时", "11:00", "13:00", True, ""),
            ("未时", "13:00", "15:00", True, ""),
            ("申时", "15:00", "17:00", True, ""),
            ("酉时", "17:00", "19:00", True, ""),
            ("戌时", "19:00", "21:00", True, ""),
            ("亥时", "21:00", "23:00", False, ""),
        ]

        hour_list = []
        for i, (zhi_name, start_bj, end_bj, is_daytime, extra_note) in enumerate(standard_hour_slots):
            cur_gan = TIAN_GAN[(start_gan_idx + i) % 10]
            cur_zhi = DI_ZHI[i]
            cur_gz = cur_gan + cur_zhi

            gan_elem = GAN_ELEMENTS[cur_gan]
            zhi_elem = ZHI_ELEMENTS[cur_zhi]

            score = 0
            tags = []

            # 基础喜用加减分（戊土喜金水，忌火土）
            if gan_elem in ["金", "水"]:
                score += 2
            elif gan_elem in ["火", "土"]:
                score -= 1

            if zhi_elem in ["金", "水"]:
                score += 2
            elif zhi_elem in ["火", "土"]:
                score -= 1

            # 天干戊癸合加分
            if cur_gan == "癸":
                score += 1
                tags.append("戊癸合财")

            # 与原局地支作用
            if cur_zhi == "午":
                score -= 3
                tags.append("冲原局子水财星")
            elif cur_zhi == "申":
                score -= 1  # 申金合财局但冲日支寅木，净+1
                tags.append("合财局但冲婚宫")
            elif cur_zhi == "酉":
                score += 1  # 辰酉六合金
                tags.append("辰酉合金生财")
            elif cur_zhi == "亥":
                score += 1  # 寅亥六合
                tags.append("寅亥六合")
            elif cur_zhi == "巳":
                score -= 2
                tags.append("寅巳相刑")
            elif cur_zhi == "戌":
                score -= 1
                tags.append("辰戌冲财库")

            # 【v3.0 核心纠偏】：检查“流时 vs 流日”是否相冲（日破时）或天克地冲
            is_day_breaker = (ZHI_CLASH_MAP.get(cur_zhi) == day_zhi)
            if is_day_breaker:
                score -= 6  # 日破凶时，一票否决重扣
                if GAN_CLASH_MAP.get(cur_gan) == day_gan:
                    tags.append("与流日天克地冲·日破大凶")
                else:
                    tags.append("冲犯流日·日破勿用")

            start_gy = self.format_solar_time(start_bj, offset_minutes)
            end_gy = self.format_solar_time(end_bj, offset_minutes)

            time_desc = f"北京时间 {start_bj}-{end_bj} / 贵阳真太阳时 {start_gy}-{end_gy}"
            if extra_note:
                time_desc += f" ({extra_note})"

            hour_list.append({
                "zhi_name": zhi_name,
                "gan_zhi": cur_gz,
                "score": score,
                "is_daytime": is_daytime,
                "is_day_breaker": is_day_breaker,
                "tags": tags,
                "time_desc": time_desc
            })

        return hour_list

    def evaluate_daily_interactions(self, lunar_data: Dict) -> Dict:
        """
        核心动力学评估 (v3.0 升级版)：
        1. 引入流年太岁维度（岁破、岁日并临）；
        2. 动态适配大运干支（壬申/癸酉自动切换）；
        3. 财运与感情文案采用优先级列表合成，彻底修复后规则覆盖前规则的 Bug；
        4. 全十天干 + 全十二地支 + 天干五合 100% 映射。
        """
        year_num = lunar_data["year"]
        year_gz = lunar_data["year_gz"]
        month_gz = lunar_data["month_gz"]
        day_gz = lunar_data["day_gz"]

        year_gan, year_zhi = year_gz[0], year_gz[1]
        month_zhi = month_gz[1]
        day_gan, day_zhi = day_gz[0], day_gz[1]

        decade_gan, decade_zhi, decade_desc = self.profile.get_decade_luck(year_num)

        latch = SeverityLatch("GREEN")
        score = 65

        day_elem = GAN_ELEMENTS[day_gan]
        day_zhi_elem = ZHI_ELEMENTS[day_zhi]
        ten_god = WU_TEN_GODS.get(day_gan, "比肩")

        month_coeffs = MONTH_ENERGY_COEFFICIENT.get(month_zhi, {"木": 1.0, "火": 1.0, "土": 1.0, "金": 1.0, "水": 1.0})
        day_gan_power = month_coeffs.get(day_elem, 1.0)
        day_zhi_power = month_coeffs.get(day_zhi_elem, 1.0)

        clashes = []
        combines = []
        penalties = []
        noble_stars = []
        cautions = []

        # 使用列表收集状态，杜绝覆盖丢失
        wealth_notes = []
        romance_notes = []

        # ----------------------------------------------------------------------
        # 规则 0：流年太岁交互扫描（《三命通会》太岁当权法则）
        # ----------------------------------------------------------------------
        is_sui_po = (ZHI_CLASH_MAP.get(day_zhi) == year_zhi)
        if is_sui_po:
            latch.update("ORANGE", f"流日{day_zhi}冲犯流年太岁{year_zhi}（岁破日）")
            score -= 14
            clashes.append(f"【岁破大耗】：流日{day_zhi}正冲流年太岁{year_zhi}，吉中藏凶，忌顶撞尊长/监管或强出头")
            cautions.append("岁破日忌大额盲目变动")

        if day_gz == year_gz:
            latch.update("ORANGE", "岁日干支伏吟")
            score -= 8
            penalties.append(f"【岁日并临】：流日与流年同为{day_gz}，气场偏亢，凡事欲速则不达")

        # ----------------------------------------------------------------------
        # 规则 1：十二地支全息动力学扫描（结合大运与原局四柱，12地支100%覆盖）
        # ----------------------------------------------------------------------
        if day_zhi == "午":
            latch.update("RED", "子午正冲，申子辰财局中神受损")
            score -= round(30 * day_zhi_power)
            clashes.append("【子午正冲】：流日午火猛烈冲克年支子水正财，震散财局中神！")
            wealth_notes.append("【红色防漏预警】财局中神逢冲，极易发生突发破费、冲动消费或亲友借贷")
            romance_notes.append("年支正财妻星受冲，注意伴侣健康或因长辈/财务事由起急躁争执")
            cautions.append("严守钱包·拒绝对外借款担保")

        elif day_zhi == "子":
            if not is_sui_po:
                latch.update("BLUE", "三合财局中神填实")
                score += round(20 * day_zhi_power)
                combines.append("【申子辰合水】：流日子水引动三合水局，正财中神归位")
                wealth_notes.append("三合财局中神填实，资金回流顺遂，极利复盘长线收息资产")
                romance_notes.append("正财妻星得位，夫妻情感温润和睦，适合共同规划家用")
            else:
                # 如 2026 丙午年逢子日：既合原局水局，又冲流年太岁午火
                score += round(8 * day_zhi_power)
                combines.append("【申子辰合水逢岁破】：流日子水虽聚原局财气，但正冲流年午火太岁（水火激战）")
                wealth_notes.append("账面有财气联动或收益机会，但逢岁破耗散，切忌贪多冒进，落袋为安")
                romance_notes.append("情缘互动活跃但易受外界长辈或琐事干扰，沟通宜低调温和")

        elif day_zhi == "申":
            latch.update("ORANGE", "申金长生位入局但冲克婚宫")
            score += round((15 - 20) * day_zhi_power)
            clashes.append("【寅申相冲 · 申入水局】：流日申金强化申子辰财局，但剧烈冲动日支寅木配偶宫")
            wealth_notes.append("食神生财有动中求财或模型优化契机，但奔波劳碌，合同细节需反复核查")
            romance_notes.append("【避吵避躁】婚宫受冲，伴侣间易因生活琐事起摩擦，宜聚少离多、少言多包容")
            cautions.extend(["伴侣沟通防硬碰硬", "驾车出行防刮蹭"])

        elif day_zhi == "酉":
            latch.update("BLUE", "辰酉六合金化食伤")
            score += round(20 * day_zhi_power)
            combines.append("【辰酉六合金】：流日酉金合动月令辰土，化生食伤金气，通关大吉！")
            wealth_notes.append("食伤生财通关有力，AI长线选股逻辑敏锐，验证财务模型灵感爆发")
            romance_notes.append("桃花合入月令，人际春风化雨，家庭相处温馨融洽")

        elif day_zhi == "辰":
            latch.update("ORANGE", "财库伏吟且辰辰自刑")
            score -= round(8 * day_zhi_power)
            penalties.append("【辰辰自刑 · 财库伏吟】：流日辰土逢月令辰土自刑伏吟，比劫重而锁水")
            wealth_notes.append("财库闭锁静守，账面流水平稳，忌主观情绪化调仓，耐心坚守长线周期")
            romance_notes.append("内心易生闷气或固执己见，莫在细枝末节上与家人较真")
            cautions.append("防自我纠结内耗")

        elif day_zhi == "戌":
            latch.update("ORANGE", "辰戌相冲动摇财库")
            score -= round(15 * day_zhi_power)
            clashes.append("【辰戌相冲】：流日戌土冲动月令辰土水库（财库大开）")
            wealth_notes.append("财库逢冲，账面资金进出波动大，利合规固定资产转换或还贷，严禁投机博弈")
            romance_notes.append("受寅午戌合火燥气牵引，脾气易急，家庭决策宜缓不宜急")
            cautions.append("大宗资金调动防误判")

        elif day_zhi == "巳":
            latch.update("ORANGE", "寅巳相刑暗生内耗")
            score -= round(12 * day_zhi_power)
            penalties.append("【寅巳相刑】：流日巳火（日主禄神）与日支寅木构成恃势之刑")
            wealth_notes.append("禄神值日行事稳健，但火旺生土克水，投资宜静观其变，勿受外界焦虑渲染")
            romance_notes.append("婚宫逢寅巳相刑，容易表面客气内心较劲，切勿将工作压力带回餐桌")
            cautions.append("心平气和·忌挑剔抱怨")

        elif day_zhi == "亥":
            latch.update("BLUE", "寅亥六合和美生木")
            score += round(14 * day_zhi_power)
            combines.append("【寅亥六合 · 巳亥微冲】：流日亥水合美日支配偶宫，同时冲动时支巳火印星")
            wealth_notes.append("偏财活水润局，利跨界思考、数据收集与资产稳健盘点")
            romance_notes.append("婚宫得六合甘霖，家庭氛围和乐，易得伴侣体贴支持，多关注子女动态")

        elif day_zhi == "寅":
            latch.update("ORANGE", "日支婚宫伏吟且引动寅巳相刑")
            score -= round(10 * day_zhi_power)
            penalties.append("【日支伏吟 · 寅巳刑动】：流日寅木与日支伏吟，且冲大运申金、刑时支巳火")
            wealth_notes.append("七杀坐支伏吟，公务责任与心理紧迫感较强，按章程推进即可，忌替人扛雷")
            romance_notes.append("配偶宫伏吟引动相刑，双方主见皆强、互不相让，今日宜各自留足独处空间")
            cautions.extend(["切忌强加观点于家人", "注意肝胆与睡眠休息"])

        elif day_zhi == "卯":
            latch.update("ORANGE", "卯辰相害穿财库且子卯相刑")
            score -= round(12 * day_zhi_power)
            penalties.append("【卯辰相害 · 子卯相刑】：流日卯木害穿月令辰土财库，且与年支子水相刑")
            wealth_notes.append("卯木穿害月令财库，需防合同条款暗坑、系统小故障或熟人背刺损耗")
            romance_notes.append("子卯无礼之刑带桃花，人际往来需注意言语分寸，伴侣间切莫翻旧账")
            cautions.append("审慎核对文书细节·谨守社交边界")

        elif day_zhi == "丑":
            score += round(5 * day_zhi_power)
            combines.append("【子丑合绊 · 辰丑微破】：流日丑土合住年支子水，与月令辰土相破")
            noble_stars.append("天乙贵人（带子丑合绊与辰丑微破，有贵人引荐但资金兑现偏慢）")
            wealth_notes.append("湿土蓄水，虽有贵人信息或长期合作洽谈，但资金易被合绊锁定，宜慢工出细活")
            romance_notes.append("感情稳定务实，但表达略显木讷沉闷，不妨主动给家人带份小礼物")

        elif day_zhi == "未":
            latch.update("ORANGE", "子未相害穿伤正财且辰未比劫刑墓")
            score -= round(12 * day_zhi_power)
            penalties.append("【子未相害】：流日未土燥气穿害年支子水正财，比劫争锋")
            noble_stars.append("天乙贵人（受子未穿害降级为虚浮贵人，谨防熟人好心办坏事或道德绑架）")
            wealth_notes.append("正财源受未土穿害，人情往来或家庭琐事开销易超支，忌听信熟人投资建议")
            romance_notes.append("子未相害易生无名委屈或隔阂，对伴侣多一分耐心，少一分说教")
            cautions.append("防人情绑架与无效社交消耗")

        if day_zhi in ["巳", "申"] and decade_zhi == "申":
            penalties.append("【巳申相合带刑】：时柱印星与申金产生刑合羁绊，警惕精力分散、顾此失彼")

        # ----------------------------------------------------------------------
        # 规则 2：十天干与天干五合深度心理映射（10天干100%覆盖，追加不覆盖）
        # ----------------------------------------------------------------------
        if day_gan == "癸":
            latch.update("BLUE", "戊癸天合正财归身")
            score += round(18 * day_gan_power)
            combines.append("【戊癸天合】：流日癸水正财与日主戊土正合（正财归位，夫妻同心）")
            wealth_notes.append("天干戊癸正合，财气主动来合，商务契约、股息分红或正职收益顺遂")
            romance_notes.append("戊癸化合有情，夫妻心意相通，极宜共进晚餐或温情夜话")

        elif day_gan == "壬":
            score += round(4 * day_gan_power)
            combines.append("【丁壬暗合】：流日壬水偏财合动时干丁火正印（防贪财坏印/分心）")
            wealth_notes.append("偏财透干外界市场噪音与暴富诱惑多，切莫心猿意马，严守AI长线高股息纪律")
            romance_notes.append("异性人缘或社交应酬活跃，对待家庭需保持专注与定力")
            cautions.append("莫受短线浮财诱惑·关注母亲长辈健康")

        elif day_gan == "庚":
            score += round(12 * day_gan_power)
            wealth_notes.append("庚金食神吐秀泄土生水，头脑极其清醒客观，极利跑通AI选股模型与深度复盘")

        elif day_gan == "辛":
            score += round(10 * day_gan_power)
            wealth_notes.append("辛金伤官生财，逆向思考与排雷嗅觉敏锐，但言辞表达宜收敛锋芒")

        elif day_gan == "戊":
            latch.update("ORANGE", "戊土比肩值日夺财")
            score -= round(12 * day_gan_power)
            wealth_notes.append("戊土比肩值日，主观执念偏重，易遇同辈竞争或熟人借钱，守好现金流不外露")
            cautions.append("戒除固执死扛·财不露白")

        elif day_gan == "己":
            latch.update("ORANGE", "己土劫财值日防破耗")
            score -= round(10 * day_gan_power)
            combines.append("【甲己合土】：流日己土合绊年干甲木七杀（劫财合杀，人情换压力）")
            wealth_notes.append("劫财合杀，虽能靠朋友关系摆平部分外部难题，但极易伴随人情破费或利益被分摊")
            cautions.append("合作账目明算账·防替人买单")

        elif day_gan == "甲":
            score += round(2 * day_gan_power)
            wealth_notes.append("甲木七杀透干引动杀印相生，风控底线意识极强，利大局把控与制度建设")

        elif day_gan == "乙":
            score += round(4 * day_gan_power)
            wealth_notes.append("乙木正官透出，行事稳重合规，利处理银行信贷、政务审批或正规机构对接")

        elif day_gan == "丙":
            score -= round(6 * day_gan_power)
            wealth_notes.append("丙火偏印生身，原局火土转燥，虽直觉敏锐但易多疑焦躁，投资宜按兵不动")

        elif day_gan == "丁":
            score += round(3 * day_gan_power)
            wealth_notes.append("丁火正印透出，心态仁厚沉稳，利阅读充电与长远规划，忌依赖拖延")

        # ----------------------------------------------------------------------
        # 规则 3：流月月令衰旺精准定性（严格区分月破与水火克战）
        # ----------------------------------------------------------------------
        if month_zhi == "亥" and day_zhi == "巳":
            penalties.append(f"【流月月破】：流日巳火遭月令亥水正冲（月破之日，旺衰仅 {day_zhi_power:.2f}），身心防虚火与倦怠")
            score -= 10
        elif month_zhi == "子" and day_zhi == "午":
            penalties.append(f"【流月月破】：流日午火遭月令子水正冲（月破之日，旺衰仅 {day_zhi_power:.2f}），财源剧震防亏损")
            score -= 10
        elif (month_zhi == "亥" and day_zhi == "午") or (month_zhi == "子" and day_zhi == "巳"):
            penalties.append(f"【月令水火克战】：流日火气受当令水气压制（旺衰系数 {day_zhi_power:.2f}），情绪易急躁不宁")
            score -= 5

        # ----------------------------------------------------------------------
        # 规则 4：合成最终文本与星级封顶
        # ----------------------------------------------------------------------
        wealth_status = "；".join(wealth_notes) if wealth_notes else "持盈保泰，遵循定投既定节奏"
        romance_status = "；".join(romance_notes) if romance_notes else "和顺从容，多包容多倾听，以柔克刚"

        score = max(10, min(100, score))
        if score >= 80:
            stars = 5
        elif score >= 68:
            stars = 4
        elif score >= 50:
            stars = 3
        elif score >= 35:
            stars = 2
        else:
            stars = 1

        if latch.level == "RED":
            stars = min(stars, 2)
        elif latch.level == "ORANGE":
            stars = min(stars, 3)

        return {
            "decade_desc": decade_desc,
            "alert_level": latch.level,
            "latch_reason": latch.latch_reason,
            "score_stars": stars,
            "score_num": score,
            "ten_god": ten_god,
            "day_element": day_elem,
            "day_zhi_element": day_zhi_elem,
            "gan_power": day_gan_power,
            "zhi_power": day_zhi_power,
            "clashes": clashes,
            "combines": combines,
            "penalties": penalties,
            "noble_stars": noble_stars,
            "wealth_status": wealth_status,
            "romance_status": romance_status,
            "cautions": list(dict.fromkeys(cautions))  # 去重保序
        }

    def calculate_fengshui_and_liaofan(self, lunar_data: Dict, eval_data: Dict) -> Dict:
        """
        【v3.0 升级】：
        1. 四象多维动态调候养生矩阵（告别二元一刀切）；
        2. 联动 Obsidian《了凡四训》功过格知识结点，生成每日专属改命实修微动作。
        """
        day_zhi = lunar_data["day_gz"][1]
        ten_god = eval_data["ten_god"]
        level = eval_data["alert_level"]

        # 1. 四象动态调候矩阵
        if day_zhi in ["巳", "午", "戌", "未"]:
            # 燥烈火土象：急需强金化燥生水
            fs = {
                "colors": "纯白、雪花银、冷浅灰（五行强金，泄燥土生真水）",
                "numbers": "4、9（金数，强化冷静理性决断）",
                "directions": "正西、西北方（金水旺位，利降燥静思与风控把关）",
                "health_tip": "今日火土燥气偏盛，易口干舌燥、胃脘胀满或心火浮越；宜饮温白开或淡菊花茶，午间静坐闭目15分钟。"
            }
        elif day_zhi in ["辰", "丑"]:
            # 湿土困水象：需金疏土、引水出库
            fs = {
                "colors": "曜石黑、深藏青搭配金属银饰（金水相生，疏通财库）",
                "numbers": "1、6、4（水金联动数，促资金与思路流转）",
                "directions": "正北、正西方（利盘活存量资产与深度研报复盘）",
                "health_tip": "湿土当值易脾胃运化迟滞、肢体困重；饮食宜少甜少油腻，傍晚快走或拉伸以助阳气升发。"
            }
        elif day_zhi in ["寅", "卯"]:
            # 官杀木旺克土象：需印星通气、食伤制衡
            fs = {
                "colors": "米白、珍珠灰点缀暖棕/暗红（金火既济，化杀生威）",
                "numbers": "4、9、2（平衡刚柔，稳固心神）",
                "directions": "正西、西南方（利跨部门协调与压力释放）",
                "health_tip": "木气偏旺克伐脾土，易出现肩颈紧绷、肝气郁结或睡眠浅；晚间宜热水泡脚，忌睡前思虑过重。"
            }
        else:
            # 申、酉、亥、子：金白水清象（喜用当令）
            fs = {
                "colors": "深海蓝、商务黑、香槟金（顺应金水喜神，聚拢正财）",
                "numbers": "1、6（北方真水数，利长线复利聚库）",
                "directions": "正北、西北方（今日财神与贵人吉方，利重大决策）",
                "health_tip": "金水流通气血顺畅，精力较为充沛；注意腰膝保暖勿受凉风，适度有氧运动可得神清气爽。"
            }

        # 2. 《了凡四训》功过格每日微修行映射
        if day_zhi in ["午", "戌"] or ten_god in ["比肩", "劫财"]:
            liaofan_action = "【破财化慈 · 主动布施】：今日有比劫夺财或冲库之象。宜主动为家人买单、请同事喝茶或做一笔小额公益捐赠，以“欢喜主动散财”应验气数，破除被动漏财（行此善举，功过格记一功）。"
        elif day_zhi in ["辰", "丑"]:
            liaofan_action = "【释执宽心 · 纳言省身】：今日湿土伏吟或墓库当值，易生固执闷气或困于牛角尖。今日刻意听取伴侣或同事的一个不同建议而不反驳，主动放下内耗执念（转念释怀一次，功过格记一功）。"
        elif day_zhi in ["申", "巳", "寅", "卯"] or level in ["ORANGE", "RED"]:
            liaofan_action = "【忍辱止嗔 · 柔语护家】：今日地支带刑害交锋，心火易起。遇伴侣唠叨或外人意见相左时，心中默念三遍“退一步海阔天空”，咽下一句生硬反驳，温和回应（忍过一次嗔怒，功过格记一功）。"
        elif day_zhi in ["酉", "亥", "子"] or ten_god in ["食神", "伤官", "正财", "偏财"]:
            liaofan_action = "【惜福精进 · 守正笃行】：今日金水喜神得力。宜专注打磨 AI 长线投资体系 1 小时，屏蔽短线噪音；晚间向伴侣或父母道一句贴心问候，惜福培福（专心致志，功过格记一功）。"
        else:
            liaofan_action = "【敬事松肩 · 功不唐捐】：今日气场中和。完成一件搁置已久的小事，允许自己不必事事完美，把紧绷的肩膀沉下来，夜间23点前安然入睡（修身养神，功过格记一功）。"

        fs["liaofan_action"] = liaofan_action
        return fs

    def generate_daily_report(self, target_date: date) -> Dict:
        lunar_data = self.get_lunar_day_data(target_date)
        day_gan = lunar_data["day_gz"][0]
        day_zhi = lunar_data["day_gz"][1]

        eval_data = self.evaluate_daily_interactions(lunar_data)
        total_offset = self.calculate_total_solar_offset_minutes(target_date)
        hours_data = self.calculate_wu_shu_dun_hours(day_gan, day_zhi, total_offset)

        # 【v3.0 核心升级】：黄金效率时与避冲时严格在日间活动窗口 (07:00-21:00) 内筛选
        daytime_hours = [h for h in hours_data if h["is_daytime"] and not h["is_day_breaker"]]
        if not daytime_hours:
            daytime_hours = [h for h in hours_data if h["is_daytime"]]

        sorted_daytime = sorted(daytime_hours, key=lambda x: x["score"], reverse=True)
        best_hour = sorted_daytime[0]

        all_daytime_for_worst = [h for h in hours_data if h["is_daytime"]]
        worst_hour = sorted(all_daytime_for_worst, key=lambda x: x["score"])[0]

        # 检查晚间（亥时 21:00-23:00）是否为高分静思吉时
        hai_hour = [h for h in hours_data if h["zhi_name"] == "亥时"][0]
        night_bonus_str = ""
        if hai_hour["score"] >= 3 and not hai_hour["is_day_breaker"]:
            night_bonus_str = f"\n* **🌙 晚间复盘吉时**：亥时（{hai_hour['gan_zhi']} · {hai_hour['time_desc']}） —— 水气润局，宜静心阅读或复盘模型。"

        best_tags = f" [{'/'.join(best_hour['tags'])}]" if best_hour["tags"] else ""
        worst_tags = f" [{'/'.join(worst_hour['tags'])}]" if worst_hour["tags"] else ""

        golden_hour_str = f"{best_hour['zhi_name']}（{best_hour['gan_zhi']}{best_tags} · {best_hour['time_desc']}）"
        caution_hour_str = f"{worst_hour['zhi_name']}（{worst_hour['gan_zhi']}{worst_tags} · {worst_hour['time_desc']}）"

        fs_energy = self.calculate_fengshui_and_liaofan(lunar_data, eval_data)

        mindset_quotes = {
            "GREEN": "“流水不争先，争的是滔滔不绝。保持节奏，万事按部就班自会水到渠成。”",
            "BLUE": "“风起于青萍之末，顺水行舟最是省力。善借工具与模型之力，不负清明心境。”",
            "ORANGE": "“事缓则圆，人缓则安。遇事退后半步冷眼旁观，切莫让一时的急躁打乱全盘布局。”",
            "RED": "“守静笃，致虚极。今天把闸门关紧、把脚步放慢，守住底线就是最大的赢家。”"
        }
        quote = mindset_quotes.get(eval_data["alert_level"], mindset_quotes["GREEN"])
        stars_str = "⭐" * eval_data["score_stars"] + "☆" * (5 - eval_data["score_stars"])

        level_badges = {
            "GREEN": "🟢 【从容平稳日】",
            "BLUE": "🔵 【顺遂契机日】",
            "ORANGE": "🟠 【审慎防范日】",
            "RED": "🔴 【重点避险日】"
        }
        badge = level_badges.get(eval_data["alert_level"], "🟢 【从容平稳日】")

        events = eval_data["clashes"] + eval_data["combines"] + eval_data["penalties"] + eval_data["noble_stars"]
        events_str = "；".join(events) if events else "原局地支安稳无大刑冲，气场中和从容。"
        cautions_str = "；".join(eval_data["cautions"]) if eval_data["cautions"] else "守住边界，不逞一时之气即可安然无虞。"

        # 1. 生成 Obsidian 归档用标准 Markdown
        md_content = f"""# 📅 每日命理指引 · {lunar_data['solar_date']}
**干支历元**：{lunar_data['year_gz']}年 · {lunar_data['month_gz']}月 · {lunar_data['day_gz']}日（农历{lunar_data['lunar_text']} · {eval_data['decade_desc']}）
**气场评级**：{badge} {stars_str} (综合能量分: {eval_data['score_num']})
**值日十神**：{eval_data['ten_god']}值日 · 天干五行属{eval_data['day_element']} (月令衰旺加权: {eval_data['gan_power']:.2f})

---

### 💼 【财富与投资微气象】
* **气场状态**：{eval_data['wealth_status']}
* **操作法则**：严格遵照 AI 既定模型与长线高股息原则，忌临时手动追涨杀跌，防熟人借钱打秋风。

### ❤️ 【爱情与人际指引】
* **相处状态**：{eval_data['romance_status']}
* **沟通指南**：对方若有琐碎唠叨，多微笑点头、不争辩对错，以柔克刚胜过千言万语。

### ⏰ 【日间吉凶时辰精算 (五鼠遁 · 滤除日破 · EOT校准)】
* **🌟 日间黄金效率时**：{golden_hour_str} —— 头脑最清晰，利深度研究、推演模型与关键决策。
* **⚠️ 日间慎言避冲时**：{caution_hour_str} —— 气场激荡易生分歧，宜静坐喝茶、少做重大决断。{night_bonus_str}

### ⚠️ 【今日避坑清单】
* **星曜交会**：{events_str}
* **核心防线**：{cautions_str}

### 🎨 【能量开运与五行调候】
* **幸运穿搭**：{fs_energy['colors']}
* **幸运数字**：{fs_energy['numbers']}
* **大吉方位**：{fs_energy['directions']}
* **身心调理**：{fs_energy['health_tip']}

### 📖 【了凡四训 · 今日功过格微修行】
* {fs_energy['liaofan_action']}

---

> 🧘‍♂️ **【今日松绑一言】**  
> {quote}
"""

        # 2. 生成专为 iOS Bark 原生通知优化的高颜值纯文本卡片（无裸露 ### 与 ** 符号）
        night_bark_line = f"\n🌙 晚间复盘：{hai_hour['zhi_name']}（{hai_hour['gan_zhi']} · {hai_hour['time_desc']}）" if night_bonus_str else ""
        bark_clean_body = f"""{badge} {stars_str} (能量分: {eval_data['score_num']})
📅 {lunar_data['solar_date']} ({lunar_data['year_gz']}年 {lunar_data['month_gz']}月 {lunar_data['day_gz']}日 · 农历{lunar_data['lunar_text']})
🧭 值日：{eval_data['ten_god']}透出（属{eval_data['day_element']} · 月令加权 {eval_data['gan_power']:.2f}）
━━━━━━━━━━━━━━━━━━
💼【财富与投资微气象】
• 状态：{eval_data['wealth_status']}
• 铁律：严守AI长线高股息模型，忌手动追涨杀跌，拒熟人借贷。

❤️【爱情与人际指引】
• 状态：{eval_data['romance_status']}
• 心法：多微笑倾听，少争辩对错，以柔克刚。

⏰【吉凶时辰 (已滤日破·贵阳真太阳时)】
🌟 黄金效率：{golden_hour_str}
⚠️ 慎言避冲：{caution_hour_str}{night_bark_line}

⚠️【今日避坑雷达】
• 交会：{events_str}
• 防线：{cautions_str}

🎨【五行调候与开运】
• 穿搭：{fs_energy['colors']}
• 数字：{fs_energy['numbers']} ｜ 方位：{fs_energy['directions']}
• 养生：{fs_energy['health_tip']}

📖【了凡四训 · 今日微修行】
• {fs_energy['liaofan_action']}
━━━━━━━━━━━━━━━━━━
🧘‍♂️ {quote}"""

        return {
            "title": f"📅 今日运势 · {lunar_data['day_gz']}日 {badge[:9]}",
            "body_md": md_content.strip(),
            "body_bark": bark_clean_body.strip(),
            "summary": f"【今日运势】{lunar_data['day_gz']}日 {badge} {eval_data['wealth_status'][:16]}...",
            "level": eval_data["alert_level"]
        }


# ==============================================================================
# 5. Bark 生产级智能推送网关 (支持动态声音与通知等级穿透)
# ==============================================================================
class BarkPusher:
    def __init__(self, bark_key: Optional[str] = None, base_url: str = "https://api.day.app"):
        resolved_key = bark_key
        if not resolved_key and os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    resolved_key = cfg.get("bark_key")
            except Exception:
                pass
        if not resolved_key:
            resolved_key = os.getenv("BARK_KEY")

        self.bark_key = resolved_key
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def save_config(bark_key: str):
        """保存 Bark Key 至本地配置文件"""
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"bark_key": bark_key.strip()}, f, ensure_ascii=False, indent=2)
        print(f"✅ Bark Key 已成功保存至配置文件: {CONFIG_FILE}")

    def push(self, title: str, content: str, alert_level: str = "GREEN",
             group: str = "每日命理指南",
             badge_icon: str = "https://img.icons8.com/color/96/compass.png",
             retry_count: int = 3) -> bool:
        """
        带超时、指数退避等待、动态提示音与 iOS 专注模式穿透的 Bark 推送网关
        """
        if not self.bark_key:
            print("[Info] Bark Key 未设置，跳过网络推送。")
            return False

        # 根据风险等级动态匹配铃声与 iOS 通知优先级
        sound_map = {
            "RED": ("alarm", "timeSensitive"),     # 红色高危：突破勿扰模式 + 警报音
            "ORANGE": ("glass", "timeSensitive"),  # 橙色防范：时效性通知 + 清脆提示音
            "BLUE": ("minuet", "active"),          # 蓝色吉日：轻快古典音
            "GREEN": ("bell", "active")            # 绿色平稳：温和钟声
        }
        sound, ios_level = sound_map.get(alert_level, ("bell", "active"))

        url = f"{self.base_url}/{self.bark_key}/"
        payload = {
            "title": title,
            "body": content,
            "group": group,
            "icon": badge_icon,
            "sound": sound,
            "level": ios_level,
            "isArchive": 1
        }

        req_data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}

        for attempt in range(1, retry_count + 1):
            try:
                req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_code = response.getcode()
                    res_body = json.loads(response.read().decode("utf-8"))
                    if res_code == 200 and res_body.get("code") == 200:
                        print(f"✅ Bark 推送成功！(第 {attempt} 次尝试 | 等级: {alert_level} | 模式: {ios_level})")
                        return True
                    else:
                        print(f"⚠️ Bark 推送返回非预期数据: {res_body}")
            except Exception as e:
                print(f"⚠️ Bark 推送发生异常 (第 {attempt}/{retry_count} 次): {e}")
                if attempt < retry_count:
                    backoff = 2 * attempt
                    print(f"⏳ 等待 {backoff} 秒后进行重试...")
                    time.sleep(backoff)

        print("❌ Bark 推送最终失败，已达到最大重试次数。")
        return False


# ==============================================================================
# 6. 生产级定时任务与命令行入口 (CLI Interface)
# ==============================================================================
def wait_until_beijing_time(target_hm: str):
    """
    【v3.0 零误差准点投递保障】：
    为应对 GitHub Actions 公共 Runner 队列延迟（通常 15~180 分钟），
    允许云端 Cron 提前唤醒容器预热环境，然后精确休眠对齐至北京时间 target_hm (如 07:00) 准秒发射。
    若因极端排队唤醒时已超过 target_hm，则不等待立即推送。
    """
    try:
        target_h, target_m = map(int, target_hm.strip().split(":"))
    except Exception:
        return
    tz_bj = timezone(timedelta(hours=8))
    now_bj = datetime.now(tz_bj)
    target_dt = now_bj.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
    diff_sec = (target_dt - now_bj).total_seconds()
    if 0 < diff_sec <= 18000:  # 最多等待 5 小时 (18000 秒)
        print(f"⏳ [云端准点锁] 当前北京时间 {now_bj.strftime('%H:%M:%S')}，容器已预热就绪，等待 {int(diff_sec)} 秒至 {target_hm}:00 准点投递...", flush=True)
        while True:
            now_bj = datetime.now(tz_bj)
            rem = (target_dt - now_bj).total_seconds()
            if rem <= 0:
                break
            time.sleep(min(rem, 30.0))
        print(f"⏰ [云端准点锁] 已抵达北京时间 {datetime.now(tz_bj).strftime('%H:%M:%S')}，立即发射推送！", flush=True)


def main():
    parser = argparse.ArgumentParser(description="每日八字动态推演与Bark智能推送引擎 v3.0")
    parser.add_argument("--push", action="store_true", help="生产定时模式：推演今日运势并推送Bark")
    parser.add_argument("--wait-until", type=str, default="", help="云端准点锁：等待至指定北京时间 (HH:MM) 再发射推送")
    parser.add_argument("--test", action="store_true", help="测试模式：执行多流日全息压力测试")
    parser.add_argument("--date", type=str, help="指定日期推演 (格式: YYYY-MM-DD)")
    parser.add_argument("--key", type=str, help="配置并保存 Bark Key 至本地")
    args = parser.parse_args()

    if args.key:
        BarkPusher.save_config(args.key)
        if not args.push and not args.date and not args.test:
            return

    profile = NativeProfile()
    engine = DailyBaziEngine(profile)
    pusher = BarkPusher()

    if args.test:
        print("=" * 80)
        print("【每日八字动态推演引擎 v3.0 终极完全体】跨流日全息压力验证")
        print("=" * 80)
        # 验证：
        # 1. 2026-11-13 (辛卯日: 检验卯酉日破时是否被成功过滤 + 卯辰穿害财库)
        # 2. 2026-11-15 (癸巳日: 检验戊癸合 + 寅巳刑 + 日间吉时过滤子时)
        # 3. 2026-11-19 (丁酉日: 检验辰酉合金大吉日)
        # 4. 2026-11-26 (甲辰日 -> 或选戊午日 2026-12-10 检验子午冲不被戊土覆盖)
        test_dates = [
            date(2026, 11, 13),  # 辛卯日
            date(2026, 11, 14),  # 壬辰日 (今日：检验丁壬合 + 辰辰自刑)
            date(2026, 11, 15),  # 癸巳日
            date(2026, 12, 10),  # 戊午日 (检验子午冲RED预警不被戊土比肩覆盖)
        ]
        for d in test_dates:
            report = engine.generate_daily_report(d)
            print(f"\n>>>>>>>>>>>>>>> 日期: {d} | 标题: {report['title']} <<<<<<<<<<<<<<<")
            print(report["body_bark"])
        return

    if args.date:
        try:
            target_d = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            return
        report = engine.generate_daily_report(target_d)
        print(report["body_bark"])
        if args.push:
            pusher.push(report["title"], report["body_bark"], alert_level=report["level"])
        return

    if args.wait_until:
        wait_until_beijing_time(args.wait_until)

    today = get_beijing_today()
    report = engine.generate_daily_report(today)
    print("=" * 80)
    print(f"【生产定时任务触发】正在处理今日北京时间 ({today}) 运势推演")
    print("=" * 80)
    print(report["body_bark"])
    print("-" * 80)

    pushed = pusher.push(report["title"], report["body_bark"], alert_level=report["level"])
    if pushed:
        print("🎉 今日命理指南已成功投递至您的 Bark 设备！")
    else:
        print("ℹ️ 今日推演已完成打印。若需推送至手机，请先配置 Bark Key。")


if __name__ == "__main__":
    main()
