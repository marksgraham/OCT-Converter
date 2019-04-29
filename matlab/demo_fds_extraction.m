file = '../file.fds';

[volume, fundus, code] = extract_fds(file);
imagesc(rot90(volume(:,:,1),3));
colormap gray;
