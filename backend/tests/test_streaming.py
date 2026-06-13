from personalops_agent.api.streaming import StreamCoalescer


def test_stream_coalescer_buffers_text_until_sentence_boundary():
    coalescer = StreamCoalescer(text_flush_chars=10)

    assert coalescer.add_text("hello") == []
    events = coalescer.add_text(" world.")

    assert events == [{"type": "token", "content": "hello world."}]


def test_stream_coalescer_emits_tool_args_incrementally():
    coalescer = StreamCoalescer()

    start_events = coalescer.start_tool("write_todos")
    arg_events = coalescer.add_tool_args('{"todos":')
    arg_events += coalescer.add_tool_args('["search"]}')
    result_events = coalescer.finish_tool("write_todos", "Updated todo list")

    assert start_events == [
        {
            "type": "tool_start",
            "phase": "started",
            "tool_call_id": None,
            "tool_name": "write_todos",
            "display_name": "规划任务",
            "status": "running",
        }
    ]
    assert arg_events == [
        {
            "type": "tool_args",
            "phase": "args",
            "tool_call_id": None,
            "tool_name": "write_todos",
            "display_name": "规划任务",
            "status": "running",
            "args_delta": '{"todos":',
        },
        {
            "type": "tool_args",
            "phase": "args",
            "tool_call_id": None,
            "tool_name": "write_todos",
            "display_name": "规划任务",
            "status": "running",
            "args_delta": '["search"]}',
        },
    ]
    assert result_events == [
        {
            "type": "tool_result",
            "phase": "completed",
            "tool_call_id": None,
            "tool_name": "write_todos",
            "display_name": "规划任务",
            "status": "done",
            "result": "任务列表已更新",
        }
    ]


def test_stream_coalescer_keeps_tool_call_id_across_lifecycle():
    coalescer = StreamCoalescer()

    start_events = coalescer.start_tool("search_web", tool_call_id="call-1")
    coalescer.add_tool_args('{"query":"东京美食"}')
    result_events = coalescer.finish_tool("search_web", "found results", tool_call_id="call-1")

    assert start_events == [
        {
            "type": "tool_start",
            "phase": "started",
            "tool_call_id": "call-1",
            "tool_name": "search_web",
            "display_name": "联网搜索",
            "status": "running",
        }
    ]
    assert result_events == [
        {
            "type": "tool_result",
            "phase": "completed",
            "tool_call_id": "call-1",
            "tool_name": "search_web",
            "display_name": "联网搜索",
            "status": "done",
            "result": "found results",
        }
    ]


def test_stream_coalescer_matches_overlapping_tool_results_by_call_id():
    coalescer = StreamCoalescer()

    coalescer.start_tool("search_web", tool_call_id="call-search")
    coalescer.add_tool_args('{"query":"上海周末路线"}')
    coalescer.start_tool("get_weather", tool_call_id="call-weather")
    coalescer.add_tool_args('{"location":"上海"}')

    search_result = coalescer.finish_tool("search_web", "search result", tool_call_id="call-search")
    weather_result = coalescer.finish_tool("get_weather", "weather result", tool_call_id="call-weather")

    assert search_result == [
        {
            "type": "tool_result",
            "phase": "completed",
            "tool_call_id": "call-search",
            "tool_name": "search_web",
            "display_name": "联网搜索",
            "status": "done",
            "result": "search result",
        }
    ]
    assert weather_result == [
        {
            "type": "tool_result",
            "phase": "completed",
            "tool_call_id": "call-weather",
            "tool_name": "get_weather",
            "display_name": "天气查询",
            "status": "done",
            "result": "weather result",
        }
    ]


def test_stream_coalescer_summarizes_write_todos_result_without_dumping_json():
    coalescer = StreamCoalescer()
    coalescer.start_tool("write_todos", tool_call_id="call-todos")

    result = coalescer.finish_tool(
        "write_todos",
        "Updated todo list to [{'content': '查询天气', 'status': 'completed'}]",
        tool_call_id="call-todos",
    )

    assert result[0]["result"] == "任务列表已更新"


def test_stream_coalescer_flushes_remaining_text_at_end():
    coalescer = StreamCoalescer()
    coalescer.add_text("final answer")

    assert coalescer.flush_text() == [{"type": "token", "content": "final answer"}]
