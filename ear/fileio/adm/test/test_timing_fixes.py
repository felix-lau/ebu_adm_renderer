from ..builder import ADMBuilder
from ..elements import AudioBlockFormatObjects
from .. import timing_fixes
from ..generate_ids import generate_ids
from fractions import Fraction
import pytest


def make_abfo(**kwargs):
    return AudioBlockFormatObjects(
        position=dict(azimuth=0.0, elevation=0.0, distance=1.0), **kwargs
    )


@pytest.fixture
def two_blocks():
    builder = ADMBuilder()
    builder.create_item_objects(
        track_index=1,
        name="MyObject 1",
        block_formats=[
            make_abfo(rtime=Fraction(0), duration=Fraction(1)),
            make_abfo(rtime=Fraction(1), duration=Fraction(1)),
        ],
    )
    generate_ids(builder.adm)

    return builder


@pytest.fixture
def one_block():
    builder = ADMBuilder()
    builder.create_item_objects(
        track_index=1,
        name="MyObject 1",
        block_formats=[make_abfo(rtime=None, duration=None)],
    )
    generate_ids(builder.adm)

    return builder


def test_fix_blockFormat_durations_expansion(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[1].rtime = Fraction(2)

    with pytest.warns(
        UserWarning,
        match="expanded duration of block format {bf.id}; was: 1, now: 2".format(
            bf=block_formats[0]
        ),
    ):
        timing_fixes.fix_blockFormat_durations(two_blocks.adm)

    assert block_formats[0].duration == Fraction(2)


def test_fix_blockFormat_durations_contraction(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].duration = Fraction(2)

    with pytest.warns(
        UserWarning,
        match="contracted duration of block format {bf.id}; was: 2, now: 1".format(
            bf=block_formats[0]
        ),
    ):
        timing_fixes.fix_blockFormat_durations(two_blocks.adm)

    assert block_formats[0].duration == Fraction(1)


def test_fix_blockFormat_durations_interpolationLength(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].duration = Fraction(2)
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction(2)

    with pytest.warns(
        UserWarning,
        match="contracted duration of block format {bf.id}; was: 2, now: 1".format(
            bf=block_formats[0]
        ),
    ):
        timing_fixes.fix_blockFormat_durations(two_blocks.adm)

    assert block_formats[0].duration == Fraction(1)
    assert block_formats[0].jumpPosition.interpolationLength == Fraction(1)


def test_fix_blockFormat_durations_correct_interpolationLength(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].duration = Fraction(2)
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction("1/2")

    with pytest.warns(
        UserWarning,
        match="contracted duration of block format {bf.id}; was: 2, now: 1".format(
            bf=block_formats[0]
        ),
    ):
        timing_fixes.fix_blockFormat_durations(two_blocks.adm)

    assert block_formats[0].duration == Fraction(1)
    assert block_formats[0].jumpPosition.interpolationLength == Fraction("1/2")


def test_fix_blockFormat_interpolationLengths(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction("2")

    with pytest.warns(
        UserWarning,
        match="contracted interpolationLength of block format {bf.id}; was: 2, now: 1".format(
            bf=block_formats[0]
        ),
    ):
        timing_fixes.fix_blockFormat_interpolationLengths(two_blocks.adm)

    assert block_formats[0].jumpPosition.interpolationLength == Fraction(1)


def test_fix_blockFormat_interpolationLengths_no_change(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction("1/2")

    timing_fixes.fix_blockFormat_interpolationLengths(two_blocks.adm)

    assert block_formats[0].jumpPosition.interpolationLength == Fraction("1/2")


def test_fix_blockFormat_times_for_audioObjects_no_change(two_blocks):
    timing_fixes.fix_blockFormat_times_for_audioObjects(two_blocks.adm)


def test_fix_blockFormat_times_for_audioObjects_delay_start(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    two_blocks.adm.audioObjects[0].start = Fraction("1/2")
    two_blocks.adm.audioObjects[0].duration = Fraction("3")

    msg = "delayed rtime of {bf.id} by 1/2 to match start time of {ao.id}".format(
        bf=block_formats[0], ao=two_blocks.adm.audioObjects[0]
    )
    with pytest.warns(UserWarning, match=msg):
        timing_fixes.fix_blockFormat_times_for_audioObjects(two_blocks.adm)

    assert block_formats[0].rtime == Fraction("1/2")


def test_fix_blockFormat_times_for_audioObjects_delay_start_after_end(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    two_blocks.adm.audioObjects[0].start = Fraction("1")
    two_blocks.adm.audioObjects[0].duration = Fraction("3")

    msg = (
        "tried to delay rtime of {bf.id} by 1 to match start time of {ao.id}, "
        "but this would be after the block end"
    ).format(bf=block_formats[0], ao=two_blocks.adm.audioObjects[0])
    with pytest.raises(ValueError, match=msg):
        timing_fixes.fix_blockFormat_times_for_audioObjects(two_blocks.adm)


def test_fix_blockFormat_times_for_audioObjects_delay_start_after_interp(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    two_blocks.adm.audioObjects[0].start = Fraction("1/2")
    two_blocks.adm.audioObjects[0].duration = Fraction("3")
    block_formats[0].jumpPosition.flag = True
    block_formats[0].jumpPosition.interpolationLength = Fraction("1/2")

    msg = (
        "tried to delay rtime of {bf.id} by 1/2 to match start time of {ao.id}, "
        "but this would be after the end of the interpolation period"
    ).format(bf=block_formats[0], ao=two_blocks.adm.audioObjects[0])
    with pytest.raises(ValueError, match=msg):
        timing_fixes.fix_blockFormat_times_for_audioObjects(two_blocks.adm)


def test_fix_blockFormat_times_for_audioObjects_advance_end(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    two_blocks.adm.audioObjects[0].start = Fraction(0)
    two_blocks.adm.audioObjects[0].duration = Fraction("1.5")

    msg = "advancing end of {bf.id} by 1/2 to match end time of {ao.id}".format(
        bf=block_formats[1], ao=two_blocks.adm.audioObjects[0]
    )
    with pytest.warns(UserWarning, match=msg):
        timing_fixes.fix_blockFormat_times_for_audioObjects(two_blocks.adm)

    assert block_formats[1].duration == Fraction("1/2")


def test_fix_blockFormat_times_for_audioObjects_advance_end_before_start(two_blocks):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    two_blocks.adm.audioObjects[0].start = Fraction(0)
    two_blocks.adm.audioObjects[0].duration = Fraction(1)

    msg = (
        "tried to advance end of {bf.id} by 1 to match end time of {ao.id}, "
        "but this would be before the block start"
    ).format(bf=block_formats[1], ao=two_blocks.adm.audioObjects[0])
    with pytest.raises(ValueError, match=msg):
        timing_fixes.fix_blockFormat_times_for_audioObjects(two_blocks.adm)


def test_fix_blockFormat_times_for_audioObjects_advance_end_interpolationLength(
    two_blocks
):
    block_formats = two_blocks.adm.audioChannelFormats[0].audioBlockFormats
    two_blocks.adm.audioObjects[0].start = Fraction(0)
    two_blocks.adm.audioObjects[0].duration = Fraction("1.25")
    block_formats[1].jumpPosition.flag = True
    block_formats[1].jumpPosition.interpolationLength = Fraction("1/2")

    with pytest.warns(UserWarning) as warnings:
        timing_fixes.fix_blockFormat_times_for_audioObjects(two_blocks.adm)
    msg = "advancing end of {bf.id} by 3/4 to match end time of {ao.id}".format(
        bf=block_formats[1], ao=two_blocks.adm.audioObjects[0]
    )
    assert str(warnings[0].message) == msg
    msg = (
        "while advancing end of {bf.id} to match end time of {ao.id}, had "
        "to reduce the interpolationLength too"
    ).format(bf=block_formats[1], ao=two_blocks.adm.audioObjects[0])
    assert str(warnings[1].message) == msg

    assert block_formats[1].duration == Fraction("1/4")
    assert block_formats[1].jumpPosition.interpolationLength == Fraction("1/4")


def test_fix_blockFormat_times_for_audioObjects_only_interp(one_block):
    [block_format] = one_block.adm.audioChannelFormats[0].audioBlockFormats
    one_block.adm.audioObjects[0].start = Fraction(0)
    one_block.adm.audioObjects[0].duration = Fraction(1)
    block_format.jumpPosition.flag = True
    block_format.jumpPosition.interpolationLength = Fraction(2)

    msg = "reduced interpolationLength of {bf.id} to match duration of {ao.id}".format(
        bf=block_format, ao=one_block.adm.audioObjects[0]
    )
    with pytest.warns(UserWarning, match=msg):
        timing_fixes.fix_blockFormat_times_for_audioObjects(one_block.adm)

    assert block_format.jumpPosition.interpolationLength == Fraction(1)