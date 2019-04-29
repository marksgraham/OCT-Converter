file = '../file.fda';

[image, code] = extract_fda(file);
imagesc(image);
colormap gray;
