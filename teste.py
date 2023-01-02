from wrappers.ttz import TTZ
import time

start = time.time()
print("Logando")
ttz = TTZ("SrYuu", "An2267saii")
ttz.login()
print(f"Tempo de login: {time.time() - start}")
start = time.time()
print("Pesquisando")
topic_id = ttz.search_uploads('Teen Titans')[0]['topic_id']
print(f"Tempo de pesquisa: {time.time() - start}")
start = time.time()
print("Pegando infos do topico")
ttz.get_topic_infos(topic_id)
print(f"Tempo pra pegar> {time.time() - start}")
ttz.logout()