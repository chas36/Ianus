"""Tests for aSc Timetables XML parser."""

from app.services.asc_xml_parser import parse_asc_xml

SAMPLE_XML = """\
<?xml version="1.0" encoding="windows-1251"?>
<timetable ascttversion="2024.24.1" importtype="database">
   <periods columns="period,name,short,starttime,endtime">
      <period name="1" short="1" period="1" starttime="8:30" endtime="9:15"/>
      <period name="2" short="2" period="2" starttime="9:30" endtime="10:15"/>
   </periods>
   <subjects columns="id,name,short,partner_id">
      <subject id="SUBJ1" name="Математика" short="Мат" partner_id=""/>
      <subject id="SUBJ2" name="Физика" short="Физ" partner_id=""/>
   </subjects>
   <teachers columns="id,name,short,gender,color,email,mobile,partner_id,firstname,lastname">
      <teacher id="TCH1" name="Иванов Иван Иванович" short="Иванов И.И."
               gender="M" color="#FF0000" email="" mobile="" partner_id=""
               firstname="Иван Иванович" lastname="Иванов"/>
   </teachers>
   <classes columns="id,name,short,classroomids,teacherid,grade,partner_id">
      <class id="CLS1" name="5А" short="5А" teacherid="TCH1"
             classroomids="ROOM1" grade="" partner_id=""/>
   </classes>
   <classrooms columns="id,name,short,capacity,buildingid,partner_id">
      <classroom id="ROOM1" name="301" short="301" capacity="*"
                 buildingid="" partner_id=""/>
   </classrooms>
   <groups columns="id,classid,name,entireclass,divisiontag,studentcount,studentids">
      <group id="GRP1" name="Весь класс" classid="CLS1"
             entireclass="1" divisiontag="0" studentids="" studentcount=""/>
      <group id="GRP2" name="1 группа" classid="CLS1"
             entireclass="0" divisiontag="1" studentids="" studentcount=""/>
   </groups>
   <lessons columns="id,subjectid,classids,groupids,teacherids,classroomids,periodspercard,periodsperweek,daysdefid,weeksdefid,termsdefid,seminargroup,capacity,partner_id">
      <lesson id="LES1" classids="CLS1" subjectid="SUBJ1" periodspercard="1"
              periodsperweek="3.0" teacherids="TCH1" classroomids="ROOM1"
              groupids="GRP1" capacity="*" seminargroup=""
              termsdefid="" weeksdefid="" daysdefid="" partner_id=""/>
      <lesson id="LES2" classids="CLS1" subjectid="SUBJ2" periodspercard="1"
              periodsperweek="2.0" teacherids="TCH1" classroomids="ROOM1"
              groupids="GRP2" capacity="*" seminargroup=""
              termsdefid="" weeksdefid="" daysdefid="" partner_id=""/>
   </lessons>
   <cards columns="lessonid,period,days,weeks,terms,classroomids">
      <card lessonid="LES1" classroomids="ROOM1" period="1" weeks="11" terms="1" days="10000"/>
      <card lessonid="LES1" classroomids="ROOM1" period="2" weeks="11" terms="1" days="01000"/>
      <card lessonid="LES1" classroomids="ROOM1" period="1" weeks="11" terms="1" days="00100"/>
      <card lessonid="LES2" classroomids="ROOM1" period="2" weeks="11" terms="1" days="10000"/>
      <card lessonid="LES2" classroomids="ROOM1" period="1" weeks="11" terms="1" days="01000"/>
   </cards>
</timetable>
""".encode("windows-1251")


def test_parse_subjects() -> None:
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["subjects"]) == 2
    assert result["subjects"][0] == {
        "asc_id": "SUBJ1",
        "name": "Математика",
        "short_name": "Мат",
    }


def test_parse_teachers() -> None:
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["teachers"]) == 1
    assert result["teachers"][0]["name"] == "Иванов Иван Иванович"
    assert result["teachers"][0]["color"] == "#FF0000"


def test_parse_classes() -> None:
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["classes"]) == 1
    assert result["classes"][0]["name"] == "5А"


def test_parse_rooms() -> None:
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["rooms"]) == 1
    assert result["rooms"][0]["name"] == "301"


def test_parse_lessons() -> None:
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["lessons"]) == 2
    lesson = result["lessons"][0]
    assert lesson["asc_id"] == "LES1"
    assert lesson["subject_asc_id"] == "SUBJ1"
    assert lesson["teacher_asc_id"] == "TCH1"
    assert lesson["class_asc_id"] == "CLS1"
    assert lesson["periods_per_week"] == 3.0


def test_parse_cards() -> None:
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["cards"]) == 5
    card = result["cards"][0]
    assert card["lesson_asc_id"] == "LES1"
    assert card["room_asc_id"] == "ROOM1"
    assert card["day"] == 1
    assert card["period"] == 1


def test_parse_cards_day_mapping() -> None:
    result = parse_asc_xml(SAMPLE_XML)
    days = [card["day"] for card in result["cards"]]
    assert days == [1, 2, 3, 1, 2]


def test_parse_lesson_group_name() -> None:
    result = parse_asc_xml(SAMPLE_XML)
    lesson = result["lessons"][1]
    assert lesson["group_name"] == "1 группа"


def test_parse_lesson_whole_class_group() -> None:
    result = parse_asc_xml(SAMPLE_XML)
    lesson = result["lessons"][0]
    assert lesson["group_name"] is None
