from wagtail import blocks


class ExtremeMeasurementBlock(blocks.StructBlock):
    station_name = blocks.CharBlock(required=True)
    extreme_value = blocks.FloatBlock(required=True)

    class Meta:
        template = 'blocks/extreme_block_item.html'


class ExtremeBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True)
    measurements = blocks.StreamBlock([
        ('measurements', ExtremeMeasurementBlock())
    ])

    class Meta:
        template = 'blocks/extreme_block.html'
