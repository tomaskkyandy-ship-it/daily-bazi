"""
================================================================================
每日八字动态推演与智能推送引擎 (Daily Bazi Deduction & Push Engine) - v2.2 生产投产版
--------------------------------------------------------------------------------
【理论基石】：
  1. 《三命通会》（明·万民英）：骨肉躯干（干支刑冲合害、神煞值日、五鼠遁起时法）
  2. 《滴天髓》（清·任铁樵）：动力神经（五行旺衰力学、生克心理学、气象调候平衡）
  *(坚决剔除管十年社会阶层的《子平真诠》与管四时宏观调候的《穷通宝鉴》)*

【工业级工程收尾 (v2.2 Production Polish)】：
  1. 字符级空格净化：确保代码严格使用标准 ASCII 空格，杜绝任何 U+00A0 (\xa0) 导致 SyntaxError。
  2. 生产级定时任务与命令行入口 (CLI Interface)：
     - 无参数直接运行 (默认生产模式)：自动获取 date.today()，生成当日报告并推送 Bark；
     - --test：运行 4 天跨流日全息压力测试；
     - --date YYYY-MM-DD：指定推演某历史或未来日期的运势；
     - --key YOUR_KEY：配置或保存 Bark Key 至本地 bark_config.json。
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

BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_today() -> date:
    """获取当前精准的北京时间日期（规避海外服务器/GitHub Actions默认UTC时区偏差）"""
    return datetime.now(BEIJING_TZ).date()

try:
    from lunar_python import Solar, Lunar
except ImportError:
    print("[Error] 请先安装 lunar_python 库: pip install lunar_python")
    sys.exit(1)


# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bark_config.json")


# ==============================================================================
# 1. 命主先天基准数据模型
# ==============================================================================
@dataclass
class NativeProfile:
    name: str = "坤哥"
    gender: str = "男"
    birth_solar: str = "1984-04-14 11:45"
    birth_location: str = "贵州贵阳"
    longitude: float = 106.63  # 贵阳东经度
    latitude: float = 26.65    # 贵阳纬度
    
    # 四柱干支
    year_gan: str = "甲"
    year_zhi: str = "子"
    month_gan: str = "戊"
    month_zhi: str = "辰"
    day_gan: str = "戊"
    day_zhi: str = "寅"
    hour_gan: str = "丁"
    hour_zhi: str = "巳"
    
    # 命盘属性
    day_master: str = "戊"  # 戊土 (偏旺, 56.4分)
    current_decade_gan: str = "壬"
    current_decade_zhi: str = "申"
    favorable_elements: List[str] = field(default_factory=lambda: ["金", "水"])
    unfavorable_elements: List[str] = field(default_factory=lambda: ["火", "土"])


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

# 月令五行旺衰系数表 (Wang-Xiang-Xiu-Qiu-Si)
# 返回五行得分系数: 旺(1.30), 相(1.15), 休(0.85), 囚(0.70), 死(0.55)
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

# 风险级别优先级字典 (用于最高风险锁存)
SEVERITY_ORDER = {
    "GREEN": 1,
    "BLUE": 2,
    "ORANGE": 3,
    "RED": 4
}


# ==============================================================================
# 3. 核心机制 1：最高风险锁存器 (Max-Severity Latch) + 积分制
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
# 4. 核心机制 2：全动态天文与微观动力学引擎
# ==============================================================================
class DailyBaziEngine:
    def __init__(self, profile: NativeProfile):
        self.profile = profile

    def calculate_equation_of_time(self, target_date: date) -> float:
        """基于 NOAA 算法计算均时差 (EOT)"""
        day_of_year = target_date.timetuple().tm_yday
        b = math.radians((360.0 / 365.25) * (day_of_year - 81))
        eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
        return eot

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
            "solar_date": target_date.strftime("%Y-%m-%d"),
            "lunar_text": f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}",
            "year_gz": lunar.getYearInGanZhiExact(),
            "month_gz": lunar.getMonthInGanZhiExact(),
            "day_gz": lunar.getDayInGanZhiExact(),
        }

    def calculate_wu_shu_dun_hours(self, day_gan: str, offset_minutes: float) -> List[Dict]:
        """五鼠遁日上起时公式全天扫描"""
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
            ("子时", "23:00", "01:00", "早子时 00:00-01:00 适用，23:00 后按次日看"),
            ("丑时", "01:00", "03:00", ""),
            ("寅时", "03:00", "05:00", ""),
            ("卯时", "05:00", "07:00", ""),
            ("辰时", "07:00", "09:00", ""),
            ("巳时", "09:00", "11:00", ""),
            ("午时", "11:00", "13:00", ""),
            ("未时", "13:00", "15:00", ""),
            ("申时", "15:00", "17:00", ""),
            ("酉时", "17:00", "19:00", ""),
            ("戌时", "19:00", "21:00", ""),
            ("亥时", "21:00", "23:00", ""),
        ]

        hour_list = []
        for i, (zhi_name, start_bj, end_bj, extra_note) in enumerate(standard_hour_slots):
            cur_gan = TIAN_GAN[(start_gan_idx + i) % 10]
            cur_zhi = DI_ZHI[i]
            cur_gz = cur_gan + cur_zhi
            
            gan_elem = GAN_ELEMENTS[cur_gan]
            zhi_elem = ZHI_ELEMENTS[cur_zhi]
            
            score = 0
            if gan_elem in ["金", "水"]: score += 2
            if zhi_elem in ["金", "水"]: score += 2
            if gan_elem in ["火", "土"]: score -= 1
            if zhi_elem in ["火", "土"]: score -= 1
            
            is_clash = False
            if cur_zhi == "午":
                score -= 3
                is_clash = True
            elif cur_zhi == "申":
                score -= 1  # 申金合水局但冲日支寅木，折损-1，净+1
            elif cur_zhi == "巳":
                score -= 2

            start_gy = self.format_solar_time(start_bj, offset_minutes)
            end_gy = self.format_solar_time(end_bj, offset_minutes)

            time_desc = f"北京时间 {start_bj}-{end_bj} / 贵阳真太阳时 {start_gy}-{end_gy}"
            if extra_note:
                time_desc += f" ({extra_note})"

            hour_list.append({
                "zhi_name": zhi_name,
                "gan_zhi": cur_gz,
                "score": score,
                "is_clash": is_clash,
                "time_desc": time_desc
            })

        return hour_list

    def evaluate_daily_interactions(self, day_gan: str, day_zhi: str, month_zhi: str) -> Dict:
        """核心动力学评估：闭环结合月令系数加权与最高风险锁存"""
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
        
        wealth_status = "持盈保泰，遵循定投既定节奏"
        romance_status = "和顺从容，多包容多倾听"

        # 规则 1：三合水局与地支大局全息扫描
        if day_zhi == "午":
            latch.update("RED", "子午正冲，申子辰财局中神受损")
            score -= round(30 * day_zhi_power)
            clashes.append("【子午正冲】：流日午火猛烈冲克年支子水，震散申子辰三合财局中神！")
            wealth_status = "【红色防漏预警】：财局中神逢冲，易有突发破费、冲动消费或亲友借款"
            cautions.append("严守钱包，拒借款")
        elif day_zhi == "子":
            latch.update("BLUE", "三合财局中神填实")
            score += round(20 * day_zhi_power)
            combines.append("【申子辰合水】：流日子水引动三合水局，财星归位！")
            wealth_status = "三合财局中神填实，资金回流顺遂，适合复盘长线资产"
        elif day_zhi == "申":
            latch.update("ORANGE", "申金长生位入局但冲克婚宫")
            score += round((15 - 20) * day_zhi_power)
            clashes.append("【寅申相冲 · 申入水局】：流日申金强化申子辰财局，但剧烈冲动日支寅木配偶宫")
            wealth_status = "财运暗流涌动有业务契机，但奔波劳碌，注意合同细节"
            romance_status = "【避吵避躁】：婚宫受冲，伴侣间易因琐事起摩擦，宜聚少离多、少言包容"
            cautions.extend(["防拌嘴", "交通防刮蹭"])
        elif day_zhi == "辰":
            score -= round(8 * day_zhi_power)
            penalties.append("【财库伏吟】：流日辰土逢月令辰土伏吟，土重分夺水气")
            wealth_status = "财库静守，账面流水平稳，不宜激进操作，耐心等待周期"
        elif day_zhi == "戌":
            latch.update("ORANGE", "辰戌相冲动摇财库")
            score -= round(15 * day_zhi_power)
            clashes.append("【辰戌相冲】：流日戌土冲动月令辰土水库（财库大开）")
            wealth_status = "财库逢冲，账面资金进出剧烈，利大额资产置换或还贷，忌盲目投资"
            cautions.append("大宗资金防误判")
        elif day_zhi == "酉":
            latch.update("BLUE", "辰酉六合金化食伤")
            score += round(20 * day_zhi_power)
            combines.append("【辰酉六合金】：流日酉金合动月令辰土，化生食伤金气，大吉！")
            wealth_status = "食伤生财，AI长线选股逻辑敏锐，模型验证灵感爆发"

        if day_zhi in ["巳", "申"]:
            penalties.append("【巳申相合带刑】：时柱印星与申金产生刑合羁绊，警惕精力分散、顾此失彼")

        # 规则 2：配偶宫【寅木】合冲刑
        if day_zhi == "巳":
            latch.update("ORANGE", "寅巳相刑暗生内耗")
            score -= round(12 * day_zhi_power)
            penalties.append("【寅巳相刑】：流日巳火与日支寅木构成恃势之刑")
            romance_status = "内心容易浮躁较劲，注意不要把职场情绪带回家庭"
            cautions.append("心平气和")
        elif day_zhi == "亥":
            latch.update("BLUE", "寅亥六合和美生木")
            score += round(15 * day_zhi_power)
            combines.append("【寅亥六合】：流日亥水与日支配偶宫六合生木（逢甘霖）")
            romance_status = "婚宫得合，家庭气氛和美，得伴侣理解体贴，相处舒心"

        # 规则 3：天干十神生克
        if day_gan == "癸":
            latch.update("BLUE", "戊癸天合正财归身")
            score += round(18 * day_gan_power)
            combines.append("【戊癸天合】：流日癸水正财与日主戊土正合（正财归位，夫妻同心）")
            wealth_status = "正财大吉，合作契约推进顺利，有稳定踏实的现金流进账"
            romance_status = "恩爱融洽，夫妻心意相通，宜共进晚餐或商量家庭未来"
        elif ten_god in ["食神", "伤官"]:
            score += round(10 * day_gan_power)
            wealth_status = "思维逻辑缜密，极利深度分析AI长线股票模型，杜绝主观冲动"
        elif ten_god in ["比肩", "劫财"]:
            latch.update("ORANGE", "比劫值日防夺财")
            score -= round(12 * day_gan_power)
            wealth_status = "比劫气盛，容易耳根子软、跟风买入或遇熟人打秋风，宜守不宜进"
            cautions.append("防被借钱")

        # 规则 4：神煞防冲降级校验
        if day_zhi == "未":
            noble_stars.append("天乙贵人（受未土刑害降级为虚浮贵人，防熟人好心办坏事）")
            score -= round(5 * day_zhi_power)
        elif day_zhi == "丑":
            noble_stars.append("天乙贵人（带辰丑破与子丑合绊，有贵人引荐但需防暗耗牵制）")
            score += round(6 * day_zhi_power)

        # 规则 5：流月月令衰旺精准定性
        if month_zhi == "亥" and day_zhi == "巳":
            penalties.append(f"【流月月破】：流日巳火遭月令亥水正冲（月破之日，旺衰仅 {day_zhi_power:.2f}），身心防虚火与倦怠")
            score -= 10
        elif month_zhi == "子" and day_zhi == "午":
            penalties.append(f"【流月月破】：流日午火遭月令子水正冲（月破之日，旺衰仅 {day_zhi_power:.2f}），财源剧震防亏损")
            score -= 10
        elif (month_zhi == "亥" and day_zhi == "午") or (month_zhi == "子" and day_zhi == "巳"):
            penalties.append(f"【月令水火克战】：流日火气受当令水气压制（旺衰系数 {day_zhi_power:.2f}），情绪易急躁不宁")
            score -= 5

        # 规则 6：星级与风险等级联动封顶
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
            "cautions": cautions
        }

    def calculate_fengshui_energy(self, day_data: Dict) -> Dict:
        """五行调候平抑算法（《滴天髓》气象平衡）"""
        zhi = day_data["day_gz"][1]
        if zhi in ["巳", "午", "戌", "未"]:
            return {
                "colors": "纯白、雪花银、冷浅灰（五行强金，化燥生水）",
                "numbers": "4、9（金数，增强理性决断）",
                "directions": "正西、西北方（利金融思考与安静复盘）",
                "health_tip": "流日燥气偏重，谨防脾胃胀气与心火亢盛，饮食宜清淡，午间闭目养神15分钟。"
            }
        else:
            return {
                "colors": "深蓝、藏青、经典黑（五行真水，正财润身）",
                "numbers": "1、6（水数，利财运聚库）",
                "directions": "正北、正西方（利商务洽谈与资产锁定）",
                "health_tip": "金水气通，筋骨舒畅，适宜适度户外散步、温水泡脚，保持周身气血流通。"
            }

    def generate_daily_report(self, target_date: date) -> Dict:
        lunar_data = self.get_lunar_day_data(target_date)
        day_gan = lunar_data["day_gz"][0]
        day_zhi = lunar_data["day_gz"][1]
        month_zhi = lunar_data["month_gz"][1]

        eval_data = self.evaluate_daily_interactions(day_gan, day_zhi, month_zhi)
        total_offset = self.calculate_total_solar_offset_minutes(target_date)
        hours_data = self.calculate_wu_shu_dun_hours(day_gan, total_offset)
        
        sorted_hours = sorted(hours_data, key=lambda x: x["score"], reverse=True)
        best_hour = sorted_hours[0]
        worst_hour = sorted_hours[-1]

        golden_hour_str = f"{best_hour['zhi_name']}（{best_hour['gan_zhi']} · {best_hour['time_desc']}）"
        caution_hour_str = f"{worst_hour['zhi_name']}（{worst_hour['gan_zhi']} · {worst_hour['time_desc']}）"

        fs_energy = self.calculate_fengshui_energy(lunar_data)

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

        md_content = f"""# 📅 每日命理指引 · {lunar_data['solar_date']}
**干支历元**：{lunar_data['year_gz']}年 · {lunar_data['month_gz']}月 · {lunar_data['day_gz']}日（农历{lunar_data['lunar_text']}）
**气场评级**：{badge} {stars_str} (综合能量分: {eval_data['score_num']})
**值日十神**：{eval_data['ten_god']}值日 · 天干五行属{eval_data['day_element']} (月令衰旺加权: {eval_data['gan_power']:.2f})

---

### 💼 【财富与投资微气象】
* **气场状态**：{eval_data['wealth_status']}
* **操作法则**：严格遵照 AI 既定模型与长线高股息原则，忌临时手动追涨杀跌，防熟人借钱打秋风。

### ❤️ 【爱情与人际指引】
* **相处状态**：{eval_data['romance_status']}
* **沟通指南**：对方若有琐碎唠叨，多微笑点头、不争辩对错，以柔克刚胜过千言万语。

### ⏰ 【吉凶时辰精算 (五鼠遁动态推算 · EOT校准)】
* **🌟 今日黄金效率时**：{golden_hour_str} —— 头脑最清晰，利深度研究、推演模型与关键决策。
* **⚠️ 今日慎言避冲时**：{caution_hour_str} —— 气场激荡易生分歧，宜静坐喝茶、少做重大决断。

### ⚠️ 【今日避坑清单】
* **星曜交会**：{events_str}
* **核心防线**：{('；'.join(eval_data['cautions'])) if eval_data['cautions'] else '守住边界，不逞一时之气即可安然无虞。'}

### 🎨 【能量开运与五行调候】
* **幸运穿搭**：{fs_energy['colors']}
* **幸运数字**：{fs_energy['numbers']}
* **大吉方位**：{fs_energy['directions']}
* **身心调理**：{fs_energy['health_tip']}

---

> 🧘‍♂️ **【今日松绑一言】**  
> {quote}
"""
        return {
            "title": f"今日运势指南 · {lunar_data['day_gz']}日",
            "body": md_content.strip(),
            "summary": f"【今日运势】{lunar_data['day_gz']}日 {badge} {eval_data['wealth_status'][:16]}... 点击查看完整指南",
            "level": eval_data["alert_level"]
        }


# ==============================================================================
# 5. Bark 生产级智能推送网关
# ==============================================================================
class BarkPusher:
    def __init__(self, bark_key: Optional[str] = None, base_url: str = "https://api.day.app"):
        # 优先级：显式传参 > 本地 bark_config.json > 环境变量 BARK_KEY
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

    def push(self, title: str, content: str, group: str = "每日命理指南", 
             badge_icon: str = "https://img.icons8.com/color/96/compass.png",
             sound: str = "bell", retry_count: int = 3) -> bool:
        """带超时、指数退避等待与状态校验的 Bark 推送网关"""
        if not self.bark_key:
            print("[Info] Bark Key 未设置，跳过网络推送。")
            print("提示：可以通过运行 `python daily_bazi_engine.py --key YOUR_KEY` 保存您的 Bark Key。")
            return False

        url = f"{self.base_url}/{self.bark_key}/"
        payload = {
            "title": title,
            "body": content,
            "group": group,
            "icon": badge_icon,
            "sound": sound,
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
                        print(f"✅ Bark 推送成功！(第 {attempt} 次尝试)")
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
def main():
    parser = argparse.ArgumentParser(description="每日八字动态推演与Bark智能推送引擎")
    parser.add_argument("--push", action="store_true", help="生产定时模式：推演今日运势并推送Bark")
    parser.add_argument("--test", action="store_true", help="测试模式：执行4日跨流日压力测试")
    parser.add_argument("--date", type=str, help="指定日期推演 (格式: YYYY-MM-DD)")
    parser.add_argument("--key", type=str, help="配置并保存 Bark Key 至本地")
    args = parser.parse_args()

    # 处理保存 Key
    if args.key:
        BarkPusher.save_config(args.key)
        if not args.push and not args.date and not args.test:
            return

    profile = NativeProfile()
    engine = DailyBaziEngine(profile)
    pusher = BarkPusher()

    # 1. 压力测试模式
    if args.test:
        print("=" * 80)
        print("【每日八字动态推演引擎 v2.2 生产投产版】压力测试运行")
        print("=" * 80)
        test_dates = [
            date(2026, 11, 12),
            date(2026, 11, 15),
            date(2026, 11, 17),
            date(2026, 11, 20)
        ]
        for d in test_dates:
            report = engine.generate_daily_report(d)
            print(f"\n>>>>>>>>>>>>>>> 日期: {d} | 等级: {report['level']} <<<<<<<<<<<<<<<")
            print(report["body"])
        return

    # 2. 指定日期推演
    if args.date:
        try:
            target_d = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            return
        report = engine.generate_daily_report(target_d)
        print(report["body"])
        if args.push:
            pusher.push(report["title"], report["body"])
        return

    # 3. 默认生产模式 (定时任务执行入口: python daily_bazi_engine.py 或 --push)
    today = get_beijing_today()
    report = engine.generate_daily_report(today)
    print("=" * 80)
    print(f"【生产定时任务触发】正在处理今日北京时间 ({today}) 运势推演")
    print("=" * 80)
    print(report["body"])
    print("-" * 80)
    
    # 执行 Bark 推送
    pushed = pusher.push(report["title"], report["body"])
    if pushed:
        print(f"🎉 今日命理指南已成功投递至您的 Bark 设备！")
    else:
        print(f"ℹ️ 今日推演已完成打印。若需推送至手机，请先配置 Bark Key。")


if __name__ == "__main__":
    main()
