from chainright import Wallet, UserProfile, PretrainingRecord

w = Wallet.create('test')
print('wallet created', w.address)

u = UserProfile(user_id='u1', name='Alice')
pr = PretrainingRecord(user=u, input_text='q', target_text='a', source_kind='seed', source_id='s1', metadata={'wallet_address': w.address})
ue = pr.to_use_event()
print('use event wallet:', ue.wallet_address)
