import os

import httpx
import streamlit as st
from google.genai import errors

from syndrome_kb import load_syndromes, search_syndromes
from consultation import (
    MODEL,
    CUSTOM_BODY_PART,
    CLINIC_INFO,
    CLINIC_NAME,
    SINGLE_SERVICES,
    PACKAGES,
    CLINIC_PRICING_INSTRUCTION,
    PATIENT_TYPES,
    OBJECTIONS,
    TAIWANESE_CLINIC_PERSONA,
    CLINICAL_GROUNDING_INSTRUCTION,
    SYNDROME_GROUNDING_INSTRUCTION,
    BODY_PART_MODELS,
    format_ntd,
    build_clinic_reference,
    get_package_quote,
    build_pricing_reference,
    build_syndrome_context,
    build_prompt,
    generate_guide,
    STAGES,
)


def render_clinic_info() -> None:
    with st.expander("📍 診所資訊與交通"):
        st.markdown(f"**{CLINIC_NAME}｜{CLINIC_INFO['branch_label']}**")
        st.write(f"地址：{CLINIC_INFO['address']}")
        st.markdown(f"電話：[{CLINIC_INFO['phone']}](tel:{CLINIC_INFO['phone_e164']})")
        st.markdown("**官方公告服務時段**")
        for period in CLINIC_INFO["hours"]:
            st.write(period)
        st.caption(CLINIC_INFO["hours_note"])
        st.markdown("**交通參考**")
        for route in CLINIC_INFO["transport"]:
            st.write(route)
        st.link_button("官方據點資訊", CLINIC_INFO["official_url"])
        if CLINIC_INFO.get("map_url"):
            st.link_button("開啟地圖導航", CLINIC_INFO["map_url"])
        if CLINIC_INFO.get("booking_url"):
            st.link_button("官方預約諮詢", CLINIC_INFO["booking_url"])
            st.caption(CLINIC_INFO["booking_note"])
        st.caption(f"資料查核：{CLINIC_INFO['verified_on']}；服務及門診異動以院所公告為準。")


def render_pricing() -> None:
    with st.expander("💰 診所價目表（新台幣）"):
        st.markdown(f"**{CLINIC_NAME}｜本頁自費治療方案，內容依個人狀況客製化安排**")
        st.markdown("**單次治療**")
        st.table([
            {
                "項目": service["name"],
                "服務內容": service["description"],
                "時間": f"{service['minutes']}分鐘",
                "單次費用": format_ntd(service["price"]),
                "備註": service["note"],
            }
            for service in SINGLE_SERVICES.values()
        ])
        st.markdown("**10堂療程方案**")
        rows = []
        for package_id in PACKAGES:
            quote = get_package_quote(package_id)
            rows.append({
                "方案": quote["name"],
                "規格": f"{quote['minutes']}分鐘 × {quote['sessions']}堂",
                "方案總價": format_ntd(quote["total"]),
                "包套折算均價": f"{format_ntd(quote['per_session'])}／堂",
                "較10次同項目單次原價節省": format_ntd(quote["saving"]),
            })
        st.table(rows)
        st.caption("首次NT$999為40分鐘初診／首次體驗價；包套均價不是單堂售價。10堂為方案規格，實際治療需求依評估決定；效期、退費及折抵規則請向診所確認。")


def reset_body_part_inputs() -> None:
    for key in ("symptom_tag", "custom_symptom", "custom_body_part"):
        st.session_state.pop(key, None)


def reset_syndrome_selection() -> None:
    st.session_state.pop("syndrome_id", None)


def main() -> None:
    st.set_page_config(page_title=f"{CLINIC_NAME}｜診間話術產生器", page_icon="🩺", layout="wide")
    st.title(f"🩺 {CLINIC_NAME}｜診間話術產生器")
    st.caption("由 Gemini 3.8 Flash 即時生成：從在地生活情境出發，先同理、說清楚，再一起決定下一步。")
    st.caption("本頁所列為自費治療方案，療程內容依個人狀況客製化安排；其他醫療服務與健保適用請洽診所確認。")
    st.info("請勿輸入姓名、電話或其他可識別患者的資料。輸入內容將傳送至 Google Gemini；生成內容需由治療師依臨床評估確認。")
    render_clinic_info()
    render_pricing()

    with st.sidebar:
        st.header("📋 情境參數設定")
        input_mode = st.radio(
            "情境來源", ["50套症候群知識庫", "部位與自訂情境"],
            key="input_mode", on_change=reset_body_part_inputs,
        )
        syndrome = None
        profile = None
        body_part, custom_body_part = CUSTOM_BODY_PART, ""
        symptom_tag = "自訂症狀"
        if input_mode == "50套症候群知識庫":
            try:
                syndromes = load_syndromes()
            except (OSError, UnicodeError, ValueError):
                syndromes = ()
                st.error("無法載入50套症候群。請確認專案根目錄的 pt-50-syndromes-database.md 存在且含完整六欄資料；也可切換部位與自訂情境。")
            if syndromes:
                category = st.selectbox(
                    "症候群分類", ["全部分類", *dict.fromkeys(item.category for item in syndromes)],
                    key="syndrome_category", on_change=reset_syndrome_selection,
                )
                query = st.text_input(
                    "搜尋症候群（支援模糊搜尋）", key="syndrome_query", max_chars=100,
                    placeholder="例如：五十肩、媽媽手、PFPS、早上 腳底",
                    on_change=reset_syndrome_selection,
                )
                candidates = tuple(item for item in syndromes if category == "全部分類" or item.category == category)
                matches = search_syndromes(candidates, query)
                by_id = {item.id: item for item in matches}
                if st.session_state.get("syndrome_id") not in by_id:
                    st.session_state.pop("syndrome_id", None)
                syndrome_id = st.selectbox(
                    "選擇症候群", list(by_id), index=None,
                    format_func=lambda item_id: by_id[item_id].label,
                    placeholder="請選擇本次溝通的症候群", key="syndrome_id",
                    on_change=reset_body_part_inputs, disabled=not matches,
                )
                st.caption(f"符合 {len(matches)} / {len(syndromes)} 套；可搜尋中文、英文、縮寫、俗稱或症狀。")
                if not matches:
                    st.info("沒有符合的症候群，請縮短關鍵字或切換全部分類。")
                syndrome = by_id.get(syndrome_id)
                if syndrome is not None:
                    custom_body_part = syndrome.category
                    symptom_tag = "症狀待評估（以所選症候群建立溝通情境）"
                    st.caption("此選擇用於建立溝通情境，不代表患者已確診；可在下方補充實際主訴。")
        else:
            body_part = st.selectbox(
                "疼痛與評估部位", [*BODY_PART_MODELS, CUSTOM_BODY_PART],
                key="body_part", on_change=reset_body_part_inputs,
            )
            if body_part == CUSTOM_BODY_PART:
                custom_body_part = st.text_input("自訂疼痛與評估部位", key="custom_body_part", max_chars=100, placeholder="例如：手肘與前臂")
            profile = BODY_PART_MODELS.get(body_part)
            symptom_options = profile["symptoms"] if profile else ["自訂症狀"]
            symptom_tag = st.selectbox("患者主訴 / 症狀", symptom_options, key="symptom_tag")
        custom_symptom = st.text_input(
            "自訂症狀（填寫後優先使用）",
            key="custom_symptom",
            max_chars=500,
            placeholder=profile["placeholder"] if profile else "請填寫實際不適、誘發動作與生活影響（勿填個資）",
        )
        stage = st.selectbox("溝通階段 / 目標", STAGES)
        objection = st.selectbox("患者猶豫 / 抗拒點", OBJECTIONS, key="objection")
        patient_type = st.selectbox("目標客群標籤", PATIENT_TYPES, key="patient_type")

    if st.button("🚀 生成話術指南", type="primary", disabled=input_mode == "50套症候群知識庫" and syndrome is None):
        symptom = custom_symptom.strip() or (symptom_tag if symptom_tag != "自訂症狀" else "")
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if body_part == CUSTOM_BODY_PART and not custom_body_part.strip():
            st.warning("請填寫自訂疼痛與評估部位。")
        elif not symptom:
            st.warning("請輸入自訂症狀，或選擇一個症狀標籤。")
        elif not api_key:
            st.error("尚未設定 GEMINI_API_KEY，請設定環境變數後重新啟動應用程式。")
        else:
            with st.spinner("正在幫你切換台灣治療師頻道，整理破局話術中..."):
                try:
                    prompt = build_prompt(symptom, stage, objection, patient_type, body_part, custom_body_part, syndrome)
                    guide = generate_guide(api_key, prompt)
                    st.session_state["guide"] = guide
                    selected_part = custom_body_part.strip() if body_part == CUSTOM_BODY_PART else BODY_PART_MODELS[body_part]["name"]
                    if syndrome is not None:
                        selected_part = syndrome.label
                    st.session_state["guide_context"] = f"{selected_part} ｜ {symptom} ｜ {stage} ｜ {objection} ｜ {patient_type}"
                except (httpx.TimeoutException, TimeoutError):
                    st.error("連線逾時，請稍後重新生成。")
                except errors.APIError as exc:
                    code = str(exc.code)
                    if code in {"401", "403"}:
                        st.error("API 金鑰無效或權限不足，請確認金鑰與 Gemini API 使用權限。")
                    elif code == "429":
                        st.error("已達 API 配額或請求頻率限制，請稍後重試或檢查帳戶配額。")
                    elif code in {"408", "504"}:
                        st.error("API 請求逾時，請稍後重新生成。")
                    elif code == "404":
                        st.error(f"找不到指定模型，請確認帳戶可使用 {MODEL}。")
                    else:
                        st.error("Gemini API 暫時無法完成請求，請確認服務狀態與 API 設定後重試。")
                except httpx.RequestError:
                    st.error("無法連線至 Gemini，請檢查網路連線後重試。")
                except ValueError:
                    st.error("模型未回傳可用文字，或回應格式無法處理，請調整情境後重試。")
                except Exception:
                    st.error("生成時發生未預期錯誤，請稍後重試或請管理員檢查套件與設定。")

    if st.session_state.get("guide"):
        st.divider()
        st.caption("以下為上次成功生成的情境：" + st.session_state["guide_context"])
        preview, copy = st.tabs(["📖 話術預覽", "📋 複製完整話術"])
        with preview:
            st.markdown(st.session_state["guide"])
        with copy:
            st.caption("將滑鼠移至程式碼區塊右上角，點選複製圖示，即可複製完整話術。")
            st.code(st.session_state["guide"], language="markdown", wrap_lines=True)
    else:
        st.write("從左側選擇患者情境，再點選「🚀 生成話術指南」。")


if __name__ == "__main__":
    main()
