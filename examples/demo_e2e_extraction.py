from file_io.e2e import E2E


filepath = '../sample_files/file.e2e'
file = E2E(filepath)
oct_volumes  = file.read_oct_volume() # returns an OCT volume with additional metadata if available

for volume in oct_volumes:
    volume.save(f'{volume.patient_id}.avi')


