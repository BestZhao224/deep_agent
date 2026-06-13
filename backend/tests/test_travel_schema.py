from personalops_agent.schemas.travel import TravelPlan


def test_travel_plan_accepts_structured_itinerary():
    plan = TravelPlan(
        destination="东京",
        summary="适合美食和城市漫步的 5 天行程。",
        days=[
            {
                "day": 1,
                "theme": "抵达与浅草散步",
                "morning": "抵达东京并前往酒店",
                "afternoon": "浅草寺与雷门",
                "evening": "上野居酒屋",
            }
        ],
        estimated_budget={"currency": "CNY", "total": 8000.0},
        weather_notes=["出行前确认实时天气。"],
        transport_tips=["优先使用地铁一日券。"],
        packing_checklist=["护照", "舒适步行鞋"],
        risks=["热门餐厅需要提前预约。"],
        sources=["https://example.com/tokyo"],
    )

    assert plan.destination == "东京"
    assert plan.days[0].theme == "抵达与浅草散步"
    assert plan.estimated_budget.currency == "CNY"
