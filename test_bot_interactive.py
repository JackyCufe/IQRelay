"""test — S1→S2a→S2b→S3a→S3b→S4→S5a→S5b→S5c→S6→Finish"""
from __future__ import annotations
import asyncio, sys
from unittest.mock import MagicMock
from botbuilder.core import TurnContext, BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity, ChannelAccount, ConversationAccount
from pipeline.pipeline import PipelineState, seed_demo_data, run_stage4_release_review

class MockAdapter(BotFrameworkAdapter):
    def __init__(self):super().__init__(BotFrameworkAdapterSettings("",""))
    async def process_activity(self,a,h,cb):
        ctx=TurnContext(self,a);await cb(ctx);return None
    async def send_activities(self,ctx,acts):
        return [MagicMock(id=f"m{i}")for i in range(len(acts))]
    async def delete_activity(self,ctx,ref,aid):pass
    async def update_activity(self,ctx,act):return act

U=ChannelAccount(id="user-001",name="Test")
B=ChannelAccount(id="bot-001",name="Bot")
C=ConversationAccount(id="c1")
T=lambda t:Activity(type="message",text=t,from_property=U,recipient=B,conversation=C,channel_id="msteams")
A=lambda d:Activity(type="message",text="",value=d,from_property=U,recipient=B,conversation=C,channel_id="msteams")
REQ="Factory QC operator Xiao Li reports: after taking photos on assembly line, operators manually classify defect types taking 30s/photo. Line processes 500 units/hr creating bottleneck. Need AI system auto-classifying scratch, dent, discoloration defects from photos in <2s."

async def test():
    seed_demo_data();adapter=MockAdapter()
    from bot import _bot,_active_pipelines
    uid="user-001";R={}

    print("TEST 1: S1 Gatekeeping");await _bot.on_turn(TurnContext(adapter,T(REQ)))
    state=_active_pipelines[uid]["state"]
    assert uid in _active_pipelines;R["s1"]=True;print("✅")

    print("TEST 2: S1→S2a");gk=state.schemas[1]["gatekeeping"]
    await _bot.on_turn(TurnContext(adapter,A({"action":"confirm_stage1","stage":1,"req_id":state.requirement_id,
        "customer_who":gk.get("customer_who",""),"usage_scenario":gk.get("usage_scenario",""),
        "problem":gk.get("problem",""),"expected_outcome":gk.get("expected_outcome",""),"next_person":"PM"})))
    assert _active_pipelines[uid]["stage"]==2;R["s2a"]=True;print("✅")

    print("TEST 3: S2a→S2b")
    await _bot.on_turn(TurnContext(adapter,A({"action":"stage2_generate","stage":2,
        "core_value":"Reduce QC time","acceptance_criteria":"1)≤2s 2)≥95%","feature_def":"Edge AI→MES","priority":"P0"})))
    assert _active_pipelines[uid]["phase"]=="confirm";R["s2b"]=True;print("✅")

    print("TEST 4: S2b→S3a")
    await _bot.on_turn(TurnContext(adapter,A({"action":"stage2_confirm","stage":2,"next_person":"RD Li"})))
    assert _active_pipelines[uid]["stage"]==3;assert _active_pipelines[uid]["phase"]=="estimate";R["s3a"]=True;print("✅")

    print("TEST 5: S3a→S3b")
    await _bot.on_turn(TurnContext(adapter,A({"action":"stage3a_confirm","stage":3,
        "tech_plan":"Azure Custom Vision","workload_days":5,"risks":"Lighting variance","next_person":"RD Li"})))
    assert _active_pipelines[uid]["phase"]=="result";R["s3b"]=True;print("✅")

    print("TEST 6: S3b→S4")
    await _bot.on_turn(TurnContext(adapter,A({"action":"stage3_submit","stage":3,
        "scenario_test":"pass","test_note":"94% accuracy",
        "approval_result":"approve","next_person":"Release Reviewer"})))
    assert _active_pipelines[uid]["stage"]==4;R["s4"]=True;print("✅")

    print("TEST 7: S4→S5a")
    await _bot.on_turn(TurnContext(adapter,A({"action":"stage4_submit","stage":4,
        "release_value":"QC<2s","version":"v1.0","release_date":"2026-06-15",
        "scenario_verified":"yes","release_risk":"medium","rollback_plan":"MES",
        "approval_result":"approve","next_person":"After-sales"})))
    assert _active_pipelines[uid]["stage"]==5;R["s5a"]=True;print("✅")

    print("TEST 8: S5a→S5b")
    await _bot.on_turn(TurnContext(adapter,A({"action":"stage5a_submit","stage":5,
        "survey_questions":"1. ok?","next_person":"Team"})))
    assert _active_pipelines[uid]["phase"]=="feedback";R["s5b"]=True;print("✅")

    print("TEST 9: S5b→S5c")
    await _bot.on_turn(TurnContext(adapter,A({"action":"stage5b_analyze","stage":5,
        "feedback_data":"customer,rating,comment\nA,3,Slow\nB,5,Great"})))
    assert 5 in state.schemas;R["s5c"]=True;print("✅")

    print("TEST 10: S5c→S6")
    await _bot.on_turn(TurnContext(adapter,A({"action":"stage5_continue","stage":5})))
    assert _active_pipelines[uid]["stage"]==6;assert 6 in state.schemas;R["s6"]=True
    print(f"✅ Foundry IQ: {len(state.schemas[6].get('knowledge_entries_written',[]))} entries")

    print("TEST 11: S6→Finish")
    await _bot.on_turn(TurnContext(adapter,A({"action":"finish","stage":6})))
    assert uid not in _active_pipelines;R["finish"]=True;print("✅")

    print("BONUS: Hard Gate");s2=PipelineState(REQ,"t");seed_demo_data();run_stage4_release_review(s2)
    _active_pipelines["gate"]={"stage":4,"phase":None,"state":s2,"status":"active"}
    await _bot.on_turn(TurnContext(adapter,A({"action":"stage4_submit","stage":4,
        "release_value":"x","version":"v1","release_date":"2026-06-15",
        "scenario_verified":"no","release_risk":"low","rollback_plan":"",
        "approval_result":"approve","next_person":"x"})))
    assert "gate" in _active_pipelines and _active_pipelines["gate"]["stage"]==4
    _active_pipelines.pop("gate",None);R["hard_gate"]=True;print("✅")

    print("\nRESULTS");ok=True
    for t,p in R.items():
        s="✅ PASS" if p else "❌ FAIL"
        if not p:ok=False
        print(f"  {s} {t}")
    print(f"\n{'🎉 ALL PASS' if ok else '❌ FAILURES'}")
    return 0 if ok else 1

if __name__=="__main__":
    sys.exit(asyncio.run(test()))