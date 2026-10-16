from juggling.evaluation import compare


def test_equal_totals_do_not_imply_accuracy():
    r={'events':[{'time':1.,'frame':30,'status':'counted'},{'time':3.,'frame':90,'status':'counted'}],
       'tracking_summary':{},'runtime_seconds':0,'config':{}}
    truth={'events':[{'time':1.03,'label':'touch'},{'time':2.,'label':'touch'}]}
    report=compare(r,truth)
    assert report['matched']==1
    assert len(report['misses'])==len(report['false_positives'])==1


def test_matching_is_one_to_one():
    r={'events':[{'time':1.,'frame':30,'status':'counted'},{'time':1.05,'frame':31,'status':'counted'}],
       'tracking_summary':{},'runtime_seconds':0,'config':{}}
    report=compare(r,{'events':[{'time':1.01,'label':'touch'}]})
    assert report['matched']==1
    assert len(report['false_positives'])==1
