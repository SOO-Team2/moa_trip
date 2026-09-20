from django import template
from ..utils import short_address

register = template.Library()

@register.filter #html에서 호출
def short_addr(value, count=3):
    return short_address(value, max_words=count, default='주소 정보 준비 중')