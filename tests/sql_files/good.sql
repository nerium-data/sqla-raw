select 'bar' as foo
{% if more %}
union
select 'baz' as quux
{% endif %}
;
